# -*- coding: utf-8 -*-
"""Small vector-index wrapper with optional FAISS backend."""

from __future__ import annotations

import os

import numpy as np

try:
    import faiss as _faiss  # type: ignore
except Exception:
    _faiss = None


class SimpleVectorIndex:
    def __init__(self, dim: int):
        self.dim = dim
        self._vectors = np.empty((0, dim), dtype="float32")

    @property
    def ntotal(self) -> int:
        return int(self._vectors.shape[0])

    def add(self, vectors):
        arr = np.asarray(vectors, dtype="float32")
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        if arr.size == 0:
            return
        if arr.shape[1] != self.dim:
            raise ValueError(f"Expected vectors with dim {self.dim}, got {arr.shape[1]}")
        self._vectors = np.vstack([self._vectors, arr])

    def search(self, query, k: int):
        arr = np.asarray(query, dtype="float32")
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        if self.ntotal == 0:
            distances = np.full((arr.shape[0], k), np.inf, dtype="float32")
            indices = np.full((arr.shape[0], k), -1, dtype="int64")
            return distances, indices

        diff = self._vectors[None, :, :] - arr[:, None, :]
        distances = np.sum(diff * diff, axis=2)
        order = np.argsort(distances, axis=1)
        topk = order[:, : min(k, self.ntotal)]

        out_dist = np.full((arr.shape[0], k), np.inf, dtype="float32")
        out_idx = np.full((arr.shape[0], k), -1, dtype="int64")

        for row in range(arr.shape[0]):
            cols = topk[row]
            size = cols.shape[0]
            out_idx[row, :size] = cols
            out_dist[row, :size] = distances[row, cols]

        return out_dist, out_idx

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            np.save(f, self._vectors, allow_pickle=False)

    @classmethod
    def load(cls, path: str, dim: int):
        index = cls(dim)
        if not os.path.exists(path):
            return index
        with open(path, 'rb') as f:
            vectors = np.load(f, allow_pickle=False)
        if vectors.ndim == 1 and vectors.size:
            vectors = vectors.reshape(1, -1)
        if vectors.size and vectors.shape[1] != dim:
            raise ValueError(f"Expected saved index dim {dim}, got {vectors.shape[1]}")
        index._vectors = np.asarray(vectors, dtype='float32')
        return index


def faiss_available() -> bool:
    return _faiss is not None


def load_vector_index(path: str, dim: int):
    if _faiss is not None:
        if os.path.exists(path):
            return _faiss.read_index(path)
        index = _faiss.IndexFlatL2(dim)
        _faiss.write_index(index, path)
        return index

    try:
        return SimpleVectorIndex.load(path, dim)
    except Exception:
        return SimpleVectorIndex(dim)


def save_vector_index(index, path: str):
    if _faiss is not None:
        _faiss.write_index(index, path)
        return

    index.save(path)
