"""Thin Panda3D helpers: static geometry from NumPy, dynamic point/line buffers,
hologram render state, procedural textures."""
from __future__ import annotations
import numpy as np
from panda3d.core import (
    Geom, GeomNode, GeomVertexFormat, GeomVertexData, GeomVertexWriter,
    GeomVertexArrayFormat, GeomTriangles, GeomLines, GeomPoints, InternalName,
    ColorBlendAttrib, TransparencyAttrib, OmniBoundingVolume, Texture, NodePath,
)


# ------------------------------------------------------------ static geometry
def make_geom_node(name, verts, tris=None, lines=None, colors=None):
    """Build a GeomNode from NumPy arrays.  colors: (N,4) per-vertex RGBA or None."""
    fmt = GeomVertexFormat.getV3c4() if colors is not None else GeomVertexFormat.getV3()
    vd = GeomVertexData(name, fmt, Geom.UHStatic)
    vd.setNumRows(len(verts))
    w = GeomVertexWriter(vd, "vertex")
    for v in verts:
        w.addData3f(float(v[0]), float(v[1]), float(v[2]))
    if colors is not None:
        cw = GeomVertexWriter(vd, "color")
        for c in colors:
            cw.addData4f(float(c[0]), float(c[1]), float(c[2]), float(c[3]))
    node = GeomNode(name)
    for data, prim_cls, k in ((tris, GeomTriangles, 3), (lines, GeomLines, 2)):
        if data is None or len(data) == 0:
            continue
        prim = prim_cls(Geom.UHStatic)
        for row in data:
            if k == 3:
                prim.addVertices(int(row[0]), int(row[1]), int(row[2]))
            else:
                prim.addVertices(int(row[0]), int(row[1]))
        g = Geom(vd)
        g.addPrimitive(prim)
        node.addGeom(g)
    return node


def holo_style(np_, order=10, additive=True, two_sided=True, depth_write=False):
    """Unlit, transparent, (additive) hologram render state."""
    np_.setTransparency(TransparencyAttrib.MAlpha)
    if additive:
        np_.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.MAdd,
                                            ColorBlendAttrib.OIncomingAlpha, ColorBlendAttrib.OOne))
    np_.setDepthWrite(depth_write)
    np_.setLightOff()
    np_.setTwoSided(two_sided)
    np_.setBin("fixed", order)
    return np_


# ------------------------------------------------------------ dynamic buffers
class DynamicGeom:
    """Per-frame updatable points or lines (positions + RGBA floats)."""

    def __init__(self, name, count, parent, primitive="points", order=30, thickness=3.0):
        arr = GeomVertexArrayFormat()
        arr.addColumn(InternalName.getVertex(), 3, Geom.NTFloat32, Geom.CPoint)
        arr.addColumn(InternalName.getColor(), 4, Geom.NTFloat32, Geom.CColor)
        fmt = GeomVertexFormat()
        fmt.addArray(arr)
        fmt = GeomVertexFormat.registerFormat(fmt)
        self.count = count
        self.vdata = GeomVertexData(name, fmt, Geom.UHDynamic)
        self.vdata.setNumRows(count)
        prim = (GeomPoints if primitive == "points" else GeomLines)(Geom.UHDynamic)
        prim.addConsecutiveVertices(0, count)
        prim.closePrimitive()
        geom = Geom(self.vdata)
        geom.addPrimitive(prim)
        node = GeomNode(name)
        node.addGeom(geom)
        node.setBounds(OmniBoundingVolume())
        node.setFinal(True)
        self.np = parent.attachNewNode(node)
        holo_style(self.np, order)
        self.np.setRenderModeThickness(thickness)
        self.buf = np.zeros((count, 7), np.float32)

    def update(self, pos, col):
        self.buf[:, :3] = pos
        self.buf[:, 3:] = col
        data = self.buf.tobytes()
        h = self.vdata.modifyArrayHandle(0)
        try:
            h.setData(data)
        except AttributeError:
            h.copyDataFrom(data)


# ------------------------------------------------------------ misc helpers
def mat4_to_np(m):
    return np.array([[m.getCell(r, c) for c in range(4)] for r in range(4)], np.float32)


def texture_from_rgba(name, arr):
    """arr: (H,W,4) uint8, row 0 = top of image."""
    h, w = arr.shape[:2]
    tex = Texture(name)
    tex.setup2dTexture(w, h, Texture.TUnsignedByte, Texture.FRgba8)
    tex.setRamImageAs(np.ascontiguousarray(arr[::-1]).tobytes(), "RGBA")
    tex.setMinfilter(Texture.FTLinear)
    tex.setMagfilter(Texture.FTLinear)
    return tex


def radial_glow_texture(size=256, color=(0.0, 0.35, 0.9), power=2.2):
    y, x = np.mgrid[-1:1:size * 1j, -1:1:size * 1j]
    r = np.sqrt(x * x + y * y)
    a = np.clip(1 - r, 0, 1) ** power
    arr = np.zeros((size, size, 4), np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = [int(c * 255) for c in color]
    arr[..., 3] = (a * 255).astype(np.uint8)
    return texture_from_rgba("glow", arr)


def scanline_texture(h=256, w=4):
    arr = np.zeros((h, w, 4), np.uint8)
    arr[::4, :, :3] = (0, 180, 255)
    arr[::4, :, 3] = 26
    tex = texture_from_rgba("scanlines", arr)
    tex.setWrapV(Texture.WMRepeat)
    return tex
