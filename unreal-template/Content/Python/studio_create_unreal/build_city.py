"""STUDIO CREATE — Unreal-side executor for ``build_city`` command files.

STATUS: NOT EXECUTED. Written against the Unreal Engine 5.6–5.8 Python API without
access to an editor; every call must be verified on the target PC before any claim.

Usage (from studio-create, headless):
    UnrealEditor-Cmd <project>.uproject -run=pythonscript -script="<this file> <command.json>"
or from the open editor: Tools > Execute Python Script, then pass the command file path.

All geometry/camera logic is computed and tested outside Unreal (``studio_create``);
this script only executes the flat action list. Generated actors carry the tag
``StudioCreate:generated`` so a regeneration replaces them and keeps manual actors.
"""

import json
import sys

import unreal

GENERATED = "StudioCreate:generated"
CUBE = "/Engine/BasicShapes/Cube.Cube"
CYLINDER = "/Engine/BasicShapes/Cylinder.Cylinder"
BASE_MATERIAL = "/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"
COLOURS = {
    "ground": (0.10, 0.11, 0.10),
    "road": (0.03, 0.03, 0.035),
    "box": (0.55, 0.52, 0.48),
    "stepped": (0.42, 0.45, 0.50),
    "tower": (0.30, 0.36, 0.42),
}
SUN_PITCH = {"dawn": -8.0, "day": -55.0, "dusk": -6.0, "night": 25.0}


def log(message):
    unreal.log(f"[STUDIO CREATE] {message}")


def actor_subsystem():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def material(name, cache):
    """One MaterialInstanceConstant per colour under /Game/StudioCreate/Materials."""
    if name in cache:
        return cache[name]
    path = f"/Game/StudioCreate/Materials/MI_{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        instance = unreal.load_asset(path)
    else:
        tools = unreal.AssetToolsHelpers.get_asset_tools()
        instance = tools.create_asset(
            f"MI_{name}",
            "/Game/StudioCreate/Materials",
            unreal.MaterialInstanceConstant,
            unreal.MaterialInstanceConstantFactoryNew(),
        )
        instance.set_editor_property("parent", unreal.load_asset(BASE_MATERIAL))
        r, g, b = COLOURS.get(name, (0.5, 0.5, 0.5))
        unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
            instance, "Color", unreal.LinearColor(r, g, b, 1.0)
        )
        unreal.EditorAssetLibrary.save_loaded_asset(instance)
    cache[name] = instance
    return instance


def tag(actor, identifier):
    actor.set_actor_label(identifier)
    actor.tags = [unreal.Name(GENERATED), unreal.Name(f"StudioCreate:id:{identifier}")]


def remove_generated():
    for actor in actor_subsystem().get_all_level_actors():
        if unreal.Name(GENERATED) in actor.tags:
            actor_subsystem().destroy_actor(actor)


def spawn_box(action, cache):
    mesh = unreal.load_asset(CUBE)
    x, y, z = action["center"]
    actor = actor_subsystem().spawn_actor_from_object(mesh, unreal.Vector(x, y, z))
    sx, sy, sz = (value / 100.0 for value in action["size"])  # Cube is 100 cm
    actor.set_actor_scale3d(unreal.Vector(sx, sy, sz))
    actor.static_mesh_component.set_material(0, material(action["material"], cache))
    tag(actor, action["id"])


def spawn_lamp(action):
    x, y, _ = action["location"]
    pole = actor_subsystem().spawn_actor_from_object(
        unreal.load_asset(CYLINDER), unreal.Vector(x, y, action["height"] / 2)
    )
    pole.set_actor_scale3d(unreal.Vector(0.15, 0.15, action["height"] / 100.0))
    tag(pole, action["id"])
    light = actor_subsystem().spawn_actor_from_class(
        unreal.PointLight, unreal.Vector(x, y, action["height"])
    )
    light.light_component.set_intensity(1500.0)
    tag(light, action["id"] + "-light")


def lighting(action):
    sun = actor_subsystem().spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 10000))
    sun.set_actor_rotation(unreal.Rotator(0.0, SUN_PITCH[action["time_of_day"]], 35.0), False)
    tag(sun, "sun")
    for cls, name in (
        (unreal.SkyAtmosphere, "sky-atmosphere"),
        (unreal.SkyLight, "sky-light"),
        (unreal.ExponentialHeightFog, "height-fog"),
    ):
        tag(actor_subsystem().spawn_actor_from_class(cls, unreal.Vector(0, 0, 0)), name)


def camera(action, cameras):
    first = action["keyframes"][0]
    actor = actor_subsystem().spawn_actor_from_class(
        unreal.CineCameraActor, unreal.Vector(*first["location"])
    )
    pitch, yaw, roll = first["rotation"]
    actor.set_actor_rotation(unreal.Rotator(roll, pitch, yaw), False)
    component = actor.get_cine_camera_component()
    component.set_editor_property("current_focal_length", action["camera"]["focal_mm"])
    component.set_editor_property("current_aperture", action["camera"]["aperture"])
    focus = component.get_editor_property("focus_settings")
    focus.set_editor_property("manual_focus_distance", action["camera"]["focus_cm"])
    component.set_editor_property("focus_settings", focus)
    tag(actor, action["name"])
    cameras[action["name"]] = actor


def sequence(action, cameras, level_id):
    numerator, _, denominator = action["fps"].partition("/")
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    path = f"/Game/Sequences/{action['name']}_{level_id}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.delete_asset(path)
    seq = tools.create_asset(
        f"{action['name']}_{level_id}", "/Game/Sequences", unreal.LevelSequence, unreal.LevelSequenceFactoryNew()
    )
    seq.set_display_rate(unreal.FrameRate(int(numerator), int(denominator or 1)))
    seq.set_playback_start(0)
    seq.set_playback_end(action["total_frames"])
    cut_track = seq.add_track(unreal.MovieSceneCameraCutTrack)
    for cut in action["cuts"]:
        binding = seq.add_possessable(cameras[cut["camera"]])
        transform = binding.add_track(unreal.MovieScene3DTransformTrack)
        section = transform.add_section()
        section.set_range(cut["start_frame"], cut["end_frame"])
        channels = section.get_all_channels()  # loc X,Y,Z, rot X(roll),Y(pitch),Z(yaw), scale
        for key in cut["keyframes"]:
            frame = unreal.FrameNumber(key["frame"])
            x, y, z = key["location"]
            pitch, yaw, roll = key["rotation"]
            for channel, value in zip(channels[:6], (x, y, z, roll, pitch, yaw)):
                channel.add_key(frame, value)
        section_cut = cut_track.add_section()
        section_cut.set_range(cut["start_frame"], cut["end_frame"])
        section_cut.set_camera_binding_id(seq.get_binding_id(binding))
    unreal.EditorAssetLibrary.save_loaded_asset(seq)
    log(f"Level Sequence {path} : {action['total_frames']} images à {action['fps']} i/s")


def run(command_path):
    with open(command_path, encoding="utf-8") as handle:
        command = json.load(handle)
    if command.get("schema_version") != 1 or command.get("command") != "build_city":
        raise RuntimeError("Fichier de commande STUDIO CREATE invalide.")
    level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    cache, cameras, level_id = {}, {}, None
    for action in command["actions"]:
        op = action["op"]
        if op == "new_level":
            level_id = action["level_id"]
            path = f"/Game/Maps/{level_id}"
            if unreal.EditorAssetLibrary.does_asset_exist(path):
                level_editor.load_level(path)
                remove_generated()  # keep manual actors, replace generated ones
            else:
                level_editor.new_level(path)
        elif op == "box":
            spawn_box(action, cache)
        elif op == "lamp":
            spawn_lamp(action)
        elif op == "lighting":
            lighting(action)
        elif op == "camera":
            camera(action, cameras)
        elif op == "sequence":
            sequence(action, cameras, level_id)
        elif op == "save_level":
            level_editor.save_current_level()
        else:
            raise RuntimeError(f"Action inconnue : {op}")
    log(f"Ville {level_id} construite : {len(command['actions'])} actions.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage : build_city.py <commande.json>")
    run(sys.argv[1])
