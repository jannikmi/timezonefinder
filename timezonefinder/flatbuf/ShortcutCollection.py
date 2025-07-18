# automatically generated by the FlatBuffers compiler, do not modify

# namespace: flatbuf

import flatbuffers
from flatbuffers.compat import import_numpy

np = import_numpy()


class ShortcutCollection:
    __slots__ = ["_tab"]

    @classmethod
    def GetRootAs(cls, buf, offset=0):
        n = flatbuffers.encode.Get(flatbuffers.packer.uoffset, buf, offset)
        x = ShortcutCollection()
        x.Init(buf, n + offset)
        return x

    @classmethod
    def GetRootAsShortcutCollection(cls, buf, offset=0):
        """This method is deprecated. Please switch to GetRootAs."""
        return cls.GetRootAs(buf, offset)

    # ShortcutCollection
    def Init(self, buf, pos):
        self._tab = flatbuffers.table.Table(buf, pos)

    # ShortcutCollection
    def Entries(self, j):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            x = self._tab.Vector(o)
            x += flatbuffers.number_types.UOffsetTFlags.py_type(j) * 4
            x = self._tab.Indirect(x)
            from timezonefinder.flatbuf.ShortcutEntry import ShortcutEntry

            obj = ShortcutEntry()
            obj.Init(self._tab.Bytes, x)
            return obj
        return None

    # ShortcutCollection
    def EntriesLength(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        if o != 0:
            return self._tab.VectorLen(o)
        return 0

    # ShortcutCollection
    def EntriesIsNone(self):
        o = flatbuffers.number_types.UOffsetTFlags.py_type(self._tab.Offset(4))
        return o == 0


def ShortcutCollectionStart(builder):
    builder.StartObject(1)


def Start(builder):
    ShortcutCollectionStart(builder)


def ShortcutCollectionAddEntries(builder, entries):
    builder.PrependUOffsetTRelativeSlot(
        0, flatbuffers.number_types.UOffsetTFlags.py_type(entries), 0
    )


def AddEntries(builder, entries):
    ShortcutCollectionAddEntries(builder, entries)


def ShortcutCollectionStartEntriesVector(builder, numElems):
    return builder.StartVector(4, numElems, 4)


def StartEntriesVector(builder, numElems):
    return ShortcutCollectionStartEntriesVector(builder, numElems)


def ShortcutCollectionEnd(builder):
    return builder.EndObject()


def End(builder):
    return ShortcutCollectionEnd(builder)
