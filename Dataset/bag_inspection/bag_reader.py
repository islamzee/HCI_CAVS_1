"""Shared helper: fast random access to messages in an uncompressed ROS 2 .mcap bag.
Author: Zeenat Islam

Reads the MCAP message index (no payloads) once, caches it, and decodes single
messages on demand using the message definitions embedded in the bag.
"""
import os, struct, pickle
from mcap.reader import make_reader
from mcap_ros2.decoder import DecoderFactory

# ---------------- configuration ----------------
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
BAG_PATH = os.path.join(REPO, "Dataset", "autonomy_demo", "autonomy_demo_0.mcap")
OUT_DIR = os.path.join(HERE, "output")
INDEX_CACHE = os.path.join(OUT_DIR, "index_cache.pkl")
# -----------------------------------------------

os.makedirs(OUT_DIR, exist_ok=True)


class Bag:
    def __init__(self, path=BAG_PATH, cache=INDEX_CACHE):
        self.f = open(path, "rb")
        self.summary = make_reader(self.f).get_summary()
        self.channels = self.summary.channels
        self.topic = {ch.topic: cid for cid, ch in self.channels.items()}
        if os.path.exists(cache) and os.path.getmtime(cache) > os.path.getmtime(path):
            self.idx, self.chunks = pickle.load(open(cache, "rb"))
        else:
            self.idx, self.chunks = self._build_index()
            pickle.dump((self.idx, self.chunks), open(cache, "wb"))
        for v in self.idx.values():
            v.sort()
        self.t0 = min(v[0][0] for v in self.idx.values())  # first message, ns since epoch
        self._rec0, self._dec = {}, {}
        self._df = DecoderFactory()

    def _build_index(self):
        """Per channel: list of (log_time_ns, chunk_no, offset_in_chunk) from MessageIndex records."""
        idx = {}
        for i, ci in enumerate(self.summary.chunk_indexes):
            if ci.compression not in ("", None):
                raise RuntimeError("compressed chunks are not supported by this reader")
            self.f.seek(min(ci.message_index_offsets.values()))
            buf = self.f.read(ci.message_index_length)
            p = 0
            while p < len(buf):
                ln = struct.unpack_from("<Q", buf, p + 1)[0]
                body = buf[p + 9:p + 9 + ln]; p += 9 + ln
                cid = struct.unpack_from("<H", body, 0)[0]
                n = struct.unpack_from("<I", body, 2)[0]
                L = idx.setdefault(cid, [])
                for k in range(n // 16):
                    lt, off = struct.unpack_from("<QQ", body, 6 + 16 * k)
                    L.append((lt, i, off))
        chunks = [(c.chunk_start_offset, c.chunk_length, c.compression) for c in self.summary.chunk_indexes]
        return idx, chunks

    # ----- timing only (no payload read) -----
    def times(self, topic):
        """Log times of every message on a topic, in seconds since the first message."""
        return [(lt - self.t0) / 1e9 for lt, _, _ in self.idx.get(self.topic[topic], [])]

    def count(self, topic):
        return len(self.idx.get(self.topic[topic], []))

    def nearest(self, topic, t):
        L = self.idx[self.topic[topic]]
        return min(range(len(L)), key=lambda j: abs((L[j][0] - self.t0) / 1e9 - t))

    # ----- payload access -----
    def _recstart(self, i):
        if i not in self._rec0:
            st = self.chunks[i][0]
            self.f.seek(st + 9 + 28); cl = struct.unpack("<I", self.f.read(4))[0]
            self._rec0[i] = st + 9 + 28 + 4 + cl + 8
        return self._rec0[i]

    def raw(self, topic, k, nbytes=None):
        """(t_seconds, CDR payload bytes) of message k. nbytes limits how much is read."""
        lt, i, off = self.idx[self.topic[topic]][k]
        self.f.seek(self._recstart(i) + off)
        op, ln = struct.unpack("<BQ", self.f.read(9))
        b = self.f.read(min(ln, nbytes + 22) if nbytes else ln)
        return (lt - self.t0) / 1e9, b[22:]

    def size(self, topic, k):
        lt, i, off = self.idx[self.topic[topic]][k]
        self.f.seek(self._recstart(i) + off)
        return struct.unpack("<BQ", self.f.read(9))[1] - 22

    def decode(self, topic, k):
        """(t_seconds, decoded ROS message) of message k."""
        cid = self.topic[topic]
        if cid not in self._dec:
            ch = self.channels[cid]
            self._dec[cid] = self._df.decoder_for(ch.message_encoding, self.summary.schemas[ch.schema_id])
        t, b = self.raw(topic, k)
        return t, self._dec[cid](b)

    def header_stamp(self, topic, k):
        """Header stamp (s) read from the first bytes of the payload, without reading the whole message."""
        t, b = self.raw(topic, k, nbytes=12)
        sec, nsec = struct.unpack("<iI", b[4:12])
        return t, sec + nsec / 1e9
