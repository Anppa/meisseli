import math
import time
import itertools
import pathlib
import functools
import copy

from build123d import *
from ocp_vscode import *

backlog = []

def log(line):
    backlog.append(line)

def dump_log():
    print()
    for ln in backlog:
        print(ln)

def top_face(bp, ax=Axis.Z):
    return bp.faces().sort_by(ax)[-1]

def bottom_face(bp, ax=Axis.Z):
    return bp.faces().sort_by(ax)[0]


PROJECT = __file__.split("/")[-1].replace(".py", "").lstrip(".")
VERSION = 1
EPS = 0.1
EXPORT = True

M2_HSI_HOLE_D = 2.9
M1_6_HOLE = 1.8
M1_6_CS_BUTT = 2.5

pcb_thk = 1.7
motor_mount_screw_dist = 9
batt_d = 18.5
batt_len = 69
spring_len = 6  # in a bit of a compressed state
outer_d = batt_d + 6
wall = 1.5
mount_len = 8
pcb_len = 11 * 2.54 + 2  # +2: add some margin
pcb_w = 5 * 2.54  # width
pcb_mount_dy = 3 * 2.54  # screw mount delta y from centerline
motor_len = 28
total_len = mount_len + pcb_thk + batt_len + spring_len + wall + pcb_len + motor_len + 2  # 2: thicker end wall for strength
motor_mount_bridging_extra = 0.3
button_thickness = 4.9  # the switch component, not cap which is also misleadingly called button :D
wall_posses = [
    [0, mount_len],  # start x pos, thickness
    [mount_len + pcb_thk + batt_len + spring_len, wall],
    [mount_len + pcb_thk + batt_len + spring_len + wall + pcb_len + motor_len - 9, 9 + 2]
    ]
pcb_mount_sc1_offx = wall_posses[1][0] + wall + 1.5 * 2.54 + 1  # +1 = margin, screw x positions
pcb_mount_sc2_offx = pcb_mount_sc1_offx + 8 * 2.54
button_xdim = 5 * 2.54
button_ydim = 3 * 2.54

def make_objects():
    with BuildSketch() as outline:
        Circle(outer_d / 2)
        boxh = batt_d + 2 * wall
        Rectangle(107, boxh, mode=Mode.INTERSECT)
    
    with BuildSketch() as inline:
        add(outline.sketch)
        offset(amount=-wall)

    with BuildSketch() as battery_lining:
        add(inline.sketch)
        Circle(18.5 / 2, mode=Mode.SUBTRACT)

    with BuildSketch() as button_sk:
        half_x = button_xdim / 2
        Rectangle(half_x, button_ydim, align=(Align.MAX, Align.CENTER))
        fillet(button_sk.vertices().group_by(Axis.X)[0], 0.5)
        roff = half_x - button_ydim / 2
        Rectangle(roff, button_ydim, align=(Align.MIN, Align.CENTER))
        with Locations((roff, 0)):
            Circle(button_ydim / 2)

    with BuildPart() as bottom_:
        with BuildSketch(Plane.YZ):
            add(outline.sketch)
        extrude(amount=total_len)
        end_edges = [bottom_face(bottom_, Axis.X).edges(), top_face(bottom_, Axis.X).edges()]
        chamfer(end_edges, wall - 0.4)
        with BuildSketch(bottom_face(bottom_, Axis.X)):
            add(inline.sketch)
        extrude(amount=-total_len, mode=Mode.SUBTRACT)
        split(bisect_by=Plane.XY, keep=Keep.BOTH)
        bottom_part, top_part = bottom_.solids()

    with BuildPart() as lid:
        add(top_part)
        # battery sleeve
        with BuildSketch(Plane.YZ.offset(mount_len + pcb_thk + 5)):
            add(battery_lining.sketch)
            with Locations((0, 1)):  # +1 = raise the thing to have a passage for + wire from switch
                Rectangle(107, 107, align=(Align.CENTER, Align.MAX), mode=Mode.SUBTRACT)
        extrude(amount=65 - 10)
        # lid screw holes
        with Locations((mount_len / 2, 0, boxh / 2), (total_len - (wall + 9) / 2, 0, boxh / 2)):
            CounterSinkHole(2.2 / 2, 4 / 2)  # M2

    with BuildPart() as bottom:
        add(bottom_part)
        for x, extr in wall_posses:
            with BuildSketch(Plane.YZ.offset(x)):
                add(inline.sketch)
            extrude(amount=extr)

        power_pcb_size = 5 * 2.54 + 1
        # power switch inlay, knob
        with Locations(Plane.YZ):
            Box(7.2, 3.8, 1.2, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        # power switch inlay, switch body
        with Locations(Plane.YZ.offset(1.2)):
            Box(11.3, 6.3, 6, align=(Align.CENTER, Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        pcb_surface_off = 1.2 * 5.3  # 5.3 = switch height
        with Locations(Plane.YZ.offset(pcb_surface_off)):
            Box(power_pcb_size, power_pcb_size, pcb_thk, mode=Mode.SUBTRACT, align=(Align.CENTER, Align.CENTER, Align.MIN))
        # power switch inlay, cable alley
        with BuildSketch(Plane.YZ.offset(pcb_surface_off)):
            with BuildLine():
                Polyline(
                    (-outer_d / 2 + wall, 0),
                    (-11 / 2, 6 / 2),  # top left corner of switch body hole above
                    (1, 0),
                    (1, -2.5 * 2.54),  # two rows down on vero
                    (-outer_d / 2 + wall + 2, -2.5 * 2.54), # +2: guessing the wall inside y location at this height                    
                    close=True)
            make_face()
        extrude(amount=-2, mode=Mode.SUBTRACT, both=True)
        # power switch label
        with BuildSketch(Plane.left):
            with Locations((-1, 0)):  # "O" is so fat
                Text("O     I", 6, font_style=FontStyle.BOLD)
        extrude(amount=-0.5, mode=Mode.SUBTRACT)
            
        # battery sleeve
        with BuildSketch(Plane.YZ.offset(mount_len + pcb_thk + 5)):
            add(battery_lining.sketch)
            with Locations((0, -1)):  # -1 = lower the thing to have a passage for + wire from switch
                Rectangle(107, 107, align=(Align.CENTER, Align.MIN), mode=Mode.SUBTRACT)
        extrude(amount=65 - 10)
        # wire alley from battery to pcb
        with Locations(Plane.YZ.offset(wall_posses[1][0])):
            with PolarLocations(outer_d / 2 - wall, 1, 135):
                Box(5, 2, wall, align=(Align.MAX, Align.MIN, Align.MIN), mode=Mode.SUBTRACT)
        # battery spring mount
        with BuildSketch(Plane.YZ.offset(wall_posses[1][0])):
            Circle(11/2)
        with BuildSketch(Plane.YZ.offset(wall_posses[1][0] - 1)):
            Circle(8.2/2)
        loft()
        with BuildSketch(Plane.YZ.offset(wall_posses[1][0])):
            Circle(6.5/2)
        extrude(amount=-1, mode=Mode.SUBTRACT)
        # wire slot
        with BuildSketch(Plane.YZ.offset(wall_posses[1][0])):
            with Locations((0, boxh/2)):
                SlotCenterToCenter(boxh, 2, rotation=90)
        extrude(amount=5, both=True, mode=Mode.SUBTRACT)

        # motor mount
        with Locations((total_len - 2, 0, motor_mount_bridging_extra)):
            Box(9, 12.5 + 2 * EPS, 10.2 + 2 * EPS + motor_mount_bridging_extra, align=(Align.MAX, Align.CENTER, Align.CENTER), mode=Mode.SUBTRACT)
        # motor axle hole
        with BuildSketch(Plane.YZ.offset(total_len)):
            Circle(2.1)
        extrude(amount=-2, mode=Mode.SUBTRACT)
        # motor mount screw holes
        with Locations(Plane.YZ.offset(total_len)):
            with GridLocations(motor_mount_screw_dist, 1, 2, 1):
                CounterSinkHole(M1_6_HOLE / 2, M1_6_CS_BUTT / 2, depth=2)

        # lid screw holes
        with BuildSketch(Plane.XY.offset(boxh / 2 - wall)):
            with Locations((mount_len / 2, 0)):
                Circle(M2_HSI_HOLE_D / 2)
        extrude(amount=-5, mode=Mode.SUBTRACT)
        with BuildSketch(Plane.XY.offset(boxh / 2 - wall)):
            with Locations((total_len - (wall + 9) / 2, 0)):
                Circle(M2_HSI_HOLE_D / 2)
        extrude(amount=-3.5, mode=Mode.SUBTRACT)

        # pcb mount screw thingys
        for x, y in (
            (pcb_mount_sc1_offx, pcb_mount_dy),
            (pcb_mount_sc2_offx, pcb_mount_dy)):
            with BuildSketch(Plane.XY) as bs:
                hd = M2_HSI_HOLE_D / 2
                with Locations((x, y)):
                    Circle(hd + 1)
                    Rectangle(M2_HSI_HOLE_D + 2 * 1, outer_d / 2 - wall - y, align=(Align.CENTER, Align.MIN))
                    Circle(hd, mode=Mode.SUBTRACT)
            f = bs.faces()[0].offset(-pcb_thk)
            mount = Solid.extrude_until(f, bottom.part, direction=(0, 0, -1))
            add(mount)
            add(mirror(mount, about=Plane.XZ))

        # button holes
        with BuildSketch(Plane.XY.offset(-boxh / 2)):
            center_x1 = pcb_mount_sc1_offx + 2 * 2.54
            center_x2 = center_x1 + 6 * 2.54
            with Locations((center_x1, 0)):
                add(button_sk.sketch, rotation=180)
            with Locations((center_x2, 0)):
                add(button_sk.sketch)
            offset(amount=0.15)  # loose hole
        extrude(amount=2 * wall, mode=Mode.SUBTRACT)

    with BuildPart() as button:
        inside_headroom = boxh / 2 - wall - pcb_thk - button_thickness - 0.3  # -0.3: some gap
        with BuildSketch():
            add(button_sk.sketch)
            offset(amount=1)
        extrude(amount=inside_headroom)
        with BuildSketch(Plane.XY.offset(inside_headroom)):
            add(button_sk.sketch)
        extrude(amount=2.5 * wall)
        chamfer(top_face(button).edges(), 0.5)

    # bit holder
    shaft_d = 3
    slit = 0.6
    shaft_len = 7
    hd = 10
    with BuildPart() as holder4:
        # for motor shaft
        with BuildSketch():
            RegularPolygon(hd / 2, 6, major_radius=False, rotation=(360/12))
            Circle(shaft_d / 2 + EPS, mode=Mode.SUBTRACT)
            with Locations((1.2, 0)):
                Rectangle(0.6, 3, align=(Align.MIN, Align.CENTER))
        extrude(amount=shaft_len + 0.5)
        # solid part in between
        with BuildSketch(Plane.XY.offset(shaft_len + 0.5)):
            RegularPolygon(hd / 2, 6, major_radius=False, rotation=(360/12))
        extrude(amount=1)
        with BuildSketch(top_face(holder4)):
            RegularPolygon(hd / 2, 6, major_radius=False, rotation=(360/12))
        extrude(amount=14)
        chamfer(top_face(holder4).edges(), 1)
        with BuildSketch(top_face(holder4)):
            RegularPolygon(2.2, 6, major_radius=False, rotation=(360/12))
        extrude(amount=-12, mode=Mode.SUBTRACT)
        # 5x1 magnet void
        with Locations(top_face(holder4).offset(-13.5)):
            Cylinder(5.4/2, 1.1, mode=Mode.SUBTRACT)

    with BuildPart() as holder635:
        add(holder4.part)
        with BuildSketch(top_face(holder635)):
            RegularPolygon(6.55/2, 6, major_radius=False, rotation=(360/12))
        extrude(amount=-12, mode=Mode.SUBTRACT)


    log(f"{total_len=} {boxh=} {outer_d=} {type(bottom.part)=}")
    
    return {
        "bottom": bottom.part,
        "button": button.part.located(Location((50, -30, 0))),
        "lid": lid.part.located(Location((0, -40, 0))).rotate(Axis.X, 180),
        "holder4": holder4.part.located(Location((20, -30, 0))),
        "holder635": holder635.part.located(Location((0, -30, 0))),
    }

st = time.time()
here = pathlib.Path(__file__).parent

try:
    objs = make_objects()
except Exception as e:
    dump_log()
    raise

if EXPORT:
    stepdir = here / "step"
    stepdir.mkdir(exist_ok=True)

for name, part in objs.items():
    if EXPORT:
        export_step(part, f"{str(here)}/step/{PROJECT}_{name}_v{VERSION}.step")
    show_object(part, name=name, reset_camera=Camera.KEEP)

dump_log()
print(f"took {time.time() - st:.1f} seconds")
