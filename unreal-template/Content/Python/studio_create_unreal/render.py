"""STUDIO CREATE — Movie Render Queue job for a generated Level Sequence.

STATUS: NOT EXECUTED. Written for the Unreal Engine 5.6–5.8 Python API without an
editor at hand; verify on the target PC. Run from the OPEN editor (Tools > Execute
Python Script): the PIE executor renders asynchronously inside the editor session.

Output: a PNG image sequence (no codec promised). ``studio-create`` assembles the
video afterwards with FFmpeg and verifies frame count and duration.
"""

import json
import sys

import unreal


def run(command_path):
    with open(command_path, encoding="utf-8") as handle:
        command = json.load(handle)
    if command.get("schema_version") != 1 or command.get("command") != "render":
        raise RuntimeError("Fichier de commande de rendu invalide.")
    subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
    queue = subsystem.get_queue()
    queue.delete_all_jobs()
    job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
    job.sequence = unreal.SoftObjectPath(command["sequence"])
    job.map = unreal.SoftObjectPath(command["map"])
    job.job_name = command["job_name"]
    config = job.get_configuration()
    config.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
    config.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
    output = config.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    output.output_directory = unreal.DirectoryPath(command["output_directory"])
    width, height = command["resolution"]
    output.output_resolution = unreal.IntPoint(width, height)
    output.file_name_format = "{sequence_name}.{frame_number}"
    anti_aliasing = config.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
    anti_aliasing.spatial_sample_count = command["anti_aliasing"]
    subsystem.render_queue_with_executor(unreal.MoviePipelinePIEExecutor)
    unreal.log(f"[STUDIO CREATE] Rendu lancé : {command['job_name']} -> {command['output_directory']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage : render.py <commande.json>")
    run(sys.argv[1])
