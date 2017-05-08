# -*- coding: utf-8 -*-

# From https://github.com/chromium/octane/blob/f84a7335bbba0e27879924b5c061c9a275c74fe8/splay.js
# customized for this repository by Nicolas Trüssel
#
# Original License Header:
# Copyright 2009 the V8 project authors. All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of Google Inc. nor the names of its
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# This benchmark is based on a JavaScript log processing module used
# by the V8 profiler to generate execution time profiles for runs of
# JavaScript applications, and it effectively measures how fast the
# JavaScript engine is at allocating nodes and reclaiming the memory
# used for old nodes. Because of the way splay trees work, the engine
# also has to deal with a lot of changes to the large tree object
# graph.

from util import run_benchmark

# Configuration.
kSplayTreeSize = 12000
kSplayTreeModifications = 1500
kSplayTreePayloadDepth = 5


def generate_payload_tree(depth, tag):
    if (depth == 0):
        return {
                'array': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                'string': 'String for key ' + tag + ' in leaf node'
                }
    else:
        return {
                'left': generate_payload_tree(depth - 1, tag),
                'right': generate_payload_tree(depth - 1, tag)
                }


def generate_key():
    seed = 49734321

    def ror(x, bits):
        return ((x & 0xffffffff) >> bits) | (x << (32-bits) & 0xffffffff)

    # Use deterministic prng from Octane's base.js
    # Robert Jenkins' 32 bit integer hash function.
    while True:
        seed = ((seed + 0x7ed55d16) + (seed << 12)) & 0xffffffff
        seed = ((seed ^ 0xc761c23c) ^ (ror(seed, 19))) & 0xffffffff
        seed = ((seed + 0x165667b1) + (seed << 5)) & 0xffffffff
        seed = ((seed + 0xd3a2646c) ^ (seed << 9)) & 0xffffffff
        seed = ((seed + 0xfd7046c5) + (seed << 3)) & 0xffffffff
        seed = ((seed ^ 0xb55a4f09) ^ (ror(seed, 16))) & 0xffffffff
        yield (seed & 0xfffffff) / (0x10000000 * 1.0)


def insert_new_node(tree):
    # Insert a new node with a unique key
    key = None
    while True:
        key = generate_key()
        if tree.find(key) is None:
            break
    #
    payload = generate_payload_tree(kSplayTreePayloadDepth, str(key))
    tree.insert(key, payload)
    return key


def splay_setup():
    tree = SplayTree()
    for i in xrange(kSplayTreeSize):
        insert_new_node(tree)
    return tree


def splay_tear_down(tree):
    # Allow the garbage collector to reclaim the memory
    # used by the splay tree no matter how we exit the
    # tear down function.
    keys = tree.export_keys()

    # Verify that the splay tree has the right size
    length = len(keys)
    if length != kSplayTreeSize:
        raise AssertionError("Splay tree has wrong size")

    # Verify that the splay tree has sorted, unique keys.
    for i in xrange(length - 1):
        if keys[i] >= keys[i + 1]:
            raise AssertionError("Splay tree not sorted")


def splay_run(tree):
    # Replace a few nodes in the splay tree
    for i in xrange(kSplayTreeModifications):
        key = insert_new_node(tree)
        greatest = tree.find_greatest_less_than(key)
        if greatest is None:
            tree.remove(key)
        else:
            tree.remove(greatest.key)


class SplayTree:
    def __init__(self):
        self._root = None

    def is_empty(self):
        return self._root is None

    def insert(self, key, value):
        if self.is_empty():
            self._root = Node(key, value)
            return

        self._splay(key)
        if self._root.key == key:
            return

        node = Node(key, value)
        if key > self._root.key:
            node.left = self._root
            node.right = self._root.right
            self._root.right = None
        else:
            node.right = self._root
            node.left = self._root.left
            self._root.left = None

        self._root = node

    def remove(self, key):
        if self.is_empty():
            raise KeyError('Key not found: ' + key)

        self._splay(key)
        if self._root.key != key:
            raise KeyError('Key not found: ' + key)

        removed = self._root
        if self._root.left is None:
            self._root = self._root.right
        else:
            right = self._root.right
            self._root = self._root.left
            # Splay to make sure that the new root has an empty right child
            self._splay(key)
            # Insert original right child as the right child of the new root
            self._root.right = right
        return removed

    def find(self, key):
        if self.is_empty():
            return None
        self._splay(key)
        return self._root if self._root.key == key else None

    def find_max(self, startNode=None):
        if self.is_empty():
            return None

        current = startNode if startNode is not None else self._root
        while current.right is not None:
            current = current.right

        return current

    def find_greatest_less_than(self, key):
        if self.is_empty():
            return None

        # Splay on the key to move the node with the given key or the last node
        # on the search path to the top of the tree
        self._splay(key)
        # Now the result is either the root node or the greatest node in the
        # left subtree
        if self._root.key < key:
            return self._root
        elif self._root.left is not None:
            return self.find_max(self._root.left)
        else:
            return None

    def export_keys(self):
        result = []
        if not self.is_empty():
            self._root._traverse(lambda node: result.append(node.key))
        return result

    def _splay(self, key):
        if self.is_empty():
            return
        # Create a dummy node. The use of the dummy node is a bit
        # counter-intuitive: The right child of the dummy node will hold
        # the L tree of the algorithm. The left child of the dummy node
        # will hold the R tree of the algorithm. Using a dummy node, left
        # and right will always be nodes and we avoid special cases.
        dummy = left = right = Node(None, None)
        current = self._root
        while True:
            if key < current.key:
                if current.left is None:
                    break
                if key < current.left.key:
                    # Rotate right
                    tmp = current.left
                    current.left = tmp.right
                    tmp.right = current
                    current = tmp
                    if current.left is None:
                        break
                # Link right
                right.left = current
                right = current
                current = current.left
            elif key > current.key:
                if current.right is None:
                    break
                if key > current.right.key:
                    # Rotate left
                    tmp = current.right
                    current.right = tmp.left
                    tmp.left = current
                    current = tmp
                    if current.right is None:
                        break
                # Link left
                left.right = current
                left = current
                current = current.right
            else:
                break
        # Assemble
        left.right = current.left
        right.left = current.right
        current.left = dummy.right
        current.right = dummy.left
        self._root = current


class Node:
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.left = None
        self.right = None

    def _traverse(self, f):
        current = self
        while current is not None:
            left = current.left
            if left is not None:
                left._traverse(f)
            f(current)
            current = current.right


if __name__ == "__main__":
    tree = splay_setup()
    run_benchmark(lambda: splay_run(tree))
    splay_tear_down(tree)
