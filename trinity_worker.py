# Python 2.7 worker executed by the EVE client's exefile /py mode.
#
# The installed client owns the closed pieces that are still required to load
# real EVE assets: Carbon Blue persistence, Granny geometry, and compiled
# Trinity. Keeping this in a short-lived process gives Jessica real
# Trinity renders without modifying code.ccp or a running game client.

from __future__ import print_function

import json
import math
import os
import sys
import traceback


def write_json(path, payload):
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, "w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


def ensure_directory(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def build_camera(angle, radius, center):
    distance = max(120.0, float(radius) * 3.1)
    elevation = distance * 0.22
    return (
        (
            center[0] + math.sin(angle) * distance,
            center[1] + elevation,
            center[2] + math.cos(angle) * distance,
        ),
        max(0.1, distance * 0.001),
        max(1000000.0, distance * 8.0),
    )


def wait_for_job(blue, tri, device, job):
    attempts = 0
    while job.status not in (tri.RJ_DONE, tri.RJ_FAILED):
        device.Render()
        blue.os.Pump()
        attempts += 1
        if attempts > 240:
            raise RuntimeError("Trinity render job did not complete")
    if job.status == tri.RJ_FAILED:
        raise RuntimeError("Trinity render job failed")


def initialize_client_resource_cache(blue):
    # Standalone /py mode intentionally skips the normal client bootstrap.
    # Register the same Remote filesystem and indexes used by autoexec so
    # res:/ paths resolve to the installed SharedCache ResFiles tree.
    if not blue.paths.IsFileSystemRegistered("Remote"):
        # The shipping packaged client gives SharedCache resources precedence
        # over the sparse local res:/ tree. Complex Black graphs such as FISFX
        # explosions can otherwise resolve a local dependency differently from
        # the game client even though the root object exists in ResFiles.
        blue.paths.RegisterFileSystemBeforeLocal("Remote")
    client_root = os.getcwd()
    cache_root = os.environ.get("ELYSIAN_JESSICA_RESFILES")
    if cache_root:
        cache_root = os.path.abspath(cache_root)
    else:
        cache_root = os.path.abspath(os.path.join(client_root, "..", "ResFiles"))
    blue.remoteFileCache.cacheFolder = cache_root
    blue.remoteFileCache.server = "https://clientresources.eveonline.com/"
    blue.remoteFileCache.backupServer = blue.remoteFileCache.server
    for filename in ("resfileindex.txt", "resfileindex_Windows.txt"):
        index_path = os.path.join(client_root, filename)
        with open(index_path, "rb") as handle:
            blue.remoteFileCache.AddFileIndex(handle.read())
    return cache_root


def resolve_icon_scene_path(dna):
    race_name = ""
    dna_parts = str(dna or "").split(":")
    if len(dna_parts) >= 3:
        race_name = dna_parts[2].split("?")[0].strip().lower()
    known_scenes = {
        "amarr": "amarr",
        "caldari": "caldari",
        "gallente": "gallente",
        "minmatar": "minmatar",
        "angel": "angel",
        "bloodraider": "bloodraider",
        "guristas": "guristas",
        "mordu": "mordu",
        "sansha": "sansha",
        "concord": "concord",
        "ore": "ore",
        "soe": "soe",
        "jove": "jove",
        "rogue": "rogue",
        "soct": "soct",
        "sleeper": "sleeper",
        "talocan": "talocan",
        "triglavian": "triglavian",
    }
    scene_name = known_scenes.get(race_name, "generic")
    return "res:/dx9/scene/iconbackground/%s.red" % scene_name


def render_turntable(
    type_id,
    dna,
    radius,
    output_dir,
    size,
    frame_count,
    render_mode,
):
    import blue
    import _trinity_dx11 as tri

    cache_root = initialize_client_resource_cache(blue)
    render_jobs = blue.classes.CreateInstance("trinity.Tr2RenderJobs")
    device = blue.classes.CreateInstance("trinity.TriDevice")
    device.deviceType = tri.TriDeviceType.SOFTWARE
    device.tickInterval = 0
    device.disableAsyncLoad = False
    device.SetRenderJobs(render_jobs)
    device.CreateWindowlessDevice()
    tri.SetShaderModel("SM_3_0_DEPTH")
    tri.settings.SetValue("newBloom", False)
    tri.settings.SetValue("dynamicExposureQualityRequirement", 2)
    tri.settings.SetValue("eveSpaceSceneDynamicLighting", True)
    tri.settings.SetValue("eveReflectionSetting", 4)
    tri.settings.SetValue("postprocessDofEnabled", False)
    tri.GetVariableStore().RegisterVariable(
        "EveSpaceSceneShadowMap",
        tri.TriTextureRes(),
    )

    sof_factory = blue.classes.CreateInstance("trinity.EveSOF")
    sof_factory.dataMgr.LoadData(
        "res:/dx9/model/spaceobjectfactory/data.black"
    )
    blue.resMan.Wait()
    space_object = sof_factory.BuildFromDNA(dna)
    if space_object is None:
        raise RuntimeError("Trinity could not build SOF DNA %s" % dna)

    for curve_name in (
        "modelRotationCurve",
        "modelTranslationCurve",
        "rotationCurve",
        "translationCurve",
    ):
        if hasattr(space_object, curve_name):
            setattr(space_object, curve_name, None)
    if hasattr(space_object, "boosters"):
        space_object.boosters = None
    if hasattr(space_object, "FreezeHighDetailMesh"):
        space_object.FreezeHighDetailMesh()
    if hasattr(space_object, "StartControllers"):
        space_object.StartControllers()

    scene_path = resolve_icon_scene_path(dna)
    scene = blue.resMan.LoadObject(scene_path)
    blue.resMan.Wait()
    if scene is None:
        scene = tri.EveSpaceScene()
        scene.postprocess = tri.Tr2PostProcess2()
    scene.sunDiffuseColor = (1.5, 1.5, 1.5, 1.0)
    scene.ambientColor = (0.32, 0.32, 0.32, 1.0)
    scene.reflectionIntensity = 1.0
    scene.backgroundReflectionIntensity = 1.0
    scene.reflectionProbe = tri.Tr2ReflectionProbe()
    scene.reflectionProbe.renderFrequency = (
        tri.ReflectionProbeRenderFrequency.AllSidesPerFrame
    )
    scene.shLightingManager = tri.Tr2ShLightingManager()
    scene.shLightingManager.primaryIntensity = 3.14
    scene.shLightingManager.secondaryIntensity = 3.14
    scene.backgroundRenderingEnabled = True
    scene.sunDirection = (-0.55, -0.72, 0.42)
    scene.objects.append(space_object)
    blue.resMan.Wait()
    scene.UpdateScene(blue.os.GetSimTime())
    model_radius = float(space_object.GetBoundingSphereRadius())
    model_center = tuple(space_object.GetBoundingSphereCenter())
    camera_radius = model_radius if model_radius > 0.0 else radius
    effect_diagnostics = []
    seen_effect_paths = set()
    for effect in space_object.Find("trinity.Tr2Effect"):
        effect_path = getattr(effect, "effectFilePath", None)
        if effect_path in seen_effect_paths:
            continue
        seen_effect_paths.add(effect_path)
        row = {
            "effectFilePath": effect_path,
        }
        effect_resource = getattr(effect, "effectResource", None)
        if effect_resource is not None:
            row["effectResourceGood"] = bool(
                getattr(effect_resource, "isGood", False)
            )
        resources = []
        for resource in getattr(effect, "resources", [])[:8]:
            resources.append({
                "name": getattr(resource, "name", None),
                "resourcePath": getattr(resource, "resourcePath", None),
                "resourceGood": bool(
                    getattr(getattr(resource, "resource", None), "isGood", False)
                ),
            })
        row["resources"] = resources
        effect_diagnostics.append(row)
        if len(effect_diagnostics) >= 16:
            break

    frames = []
    for index in range(frame_count):
        angle = (float(index) / float(frame_count)) * math.pi * 2.0
        filename = "frame-%03d.jpg" % index
        output_path = os.path.join(output_dir, filename)
        eye, near_plane, far_plane = build_camera(
            angle,
            camera_radius,
            model_center,
        )
        # Keep the authored icon-scene key light on the viewed hemisphere as
        # the turntable rotates. The ship itself is not rotated, so this avoids
        # spending half the sequence looking at an unlit silhouette.
        scene.sunDirection = (
            math.sin(angle),
            -0.35,
            math.cos(angle),
        )

        view = tri.TriView()
        view.SetLookAtPosition(
            eye,
            model_center,
            (0.0, 1.0, 0.0),
        )
        projection = tri.TriProjection()
        projection.PerspectiveFov(0.84, 1.0, near_plane, far_plane)

        render_target = tri.Tr2RenderTarget(
            size,
            size,
            1,
            tri.PIXEL_FORMAT.B8G8R8X8_UNORM,
        )
        render_driver = tri.EveSpaceSceneRenderDriver()
        render_driver.name = "ElysianDemoToolDriver-%03d" % index
        render_driver.scene = scene
        render_driver.view = view
        render_driver.projection = projection
        render_driver.clearColor = (0.006, 0.012, 0.025, 1.0)
        render_driver.internalPixelFormat = tri.PIXEL_FORMAT.R16G16B16A16_FLOAT
        render_driver.shadowQuality = 0
        render_driver.antiAliasingQuality = 0
        render_driver.aoQuality = 0
        render_driver.volumetricQuality = 0
        render_driver.postProcessingQuality = 0
        render_driver.visualizeMethod = {
            "material": 0,
            "texcoord": 1,
            "white": 3,
            "overdraw": 4,
            "wireframe": 5,
        }.get(render_mode, 3)
        render_driver.enableUpscaling = False
        render_driver.enableDistortion = False
        render_driver.forceOpaqueBuffer = True
        render_driver.SSAO = tri.Tr2SSAO()

        execute_node = tri.Tr2StepExecuteRenderNode()
        execute_node.name = "ElysianDemoToolScene-%03d" % index
        execute_node.node = render_driver
        execute_node.destinationTarget = render_target
        execute_node.clearTargetOnFailure = True

        job = tri.TriRenderJob()
        job.name = "ElysianDemoTool-%03d" % index
        # EveSpaceScene::Render is intentionally empty in CCP's public Trinity
        # source. Space scenes must execute through EveSpaceSceneRenderDriver,
        # which owns the native multipass scene pipeline.
        job.steps.append(execute_node)
        # CCP's icon renderer schedules the Jessica job once to prepare native
        # resources and once more for the frame that is read back.
        for _ in range(2):
            job.status = tri.RJ_INIT
            render_jobs.once.append(job)
            wait_for_job(blue, tri, device, job)
            blue.resMan.Wait()
            blue.os.Pump()

        tri.Tr2HostBitmap(render_target).Save(output_path)
        frames.append(filename)

    missing = [
        filename
        for filename in frames
        if not os.path.isfile(os.path.join(output_dir, filename))
    ]
    if missing:
        raise RuntimeError("Trinity did not write frames: %s" % ", ".join(missing))

    return {
        "typeID": type_id,
        "dna": dna,
        "radius": radius,
        "modelRadius": model_radius,
        "modelCenter": model_center,
        "size": size,
        "frameCount": frame_count,
        "frames": frames,
        "renderMode": render_mode,
        "trinityPlatform": "dx11",
        "shaderModel": str(tri.GetShaderModel()),
        "resourceCache": cache_root,
        "scenePath": scene_path,
        "effectDiagnostics": effect_diagnostics,
    }


def main():
    if len(sys.argv) < 8:
        raise RuntimeError(
            "usage: trinity_worker.py TYPE_ID DNA RADIUS OUTPUT_DIR SIZE FRAMES STATUS_JSON [MODE]"
        )

    type_id = int(sys.argv[1])
    dna = sys.argv[2]
    radius = float(sys.argv[3])
    output_dir = os.path.abspath(sys.argv[4])
    size = int(sys.argv[5])
    frame_count = int(sys.argv[6])
    status_path = os.path.abspath(sys.argv[7])
    render_mode = sys.argv[8] if len(sys.argv) > 8 else "white"
    ensure_directory(output_dir)

    import blue
    import stackless

    outcome = {}

    def run_render():
        try:
            outcome["result"] = render_turntable(
                type_id,
                dna,
                radius,
                output_dir,
                size,
                frame_count,
                render_mode,
            )
        except Exception:
            outcome["error"] = traceback.format_exc()

    task = stackless.tasklet(run_render)()
    while task.alive:
        blue.os.Pump()

    try:
        if "error" in outcome:
            raise RuntimeError(outcome["error"])
        result = outcome["result"]
        result["ok"] = True
        write_json(status_path, result)
        print("TRINITY_RENDER_OK %s" % type_id)
        return 0
    except Exception:
        error = traceback.format_exc()
        write_json(status_path, {
            "ok": False,
            "typeID": type_id,
            "error": error,
        })
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
