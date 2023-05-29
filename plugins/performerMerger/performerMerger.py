import json
import sys

try:
    import stashapi.log as log
    from stashapi.stashapp import StashInterface
except ModuleNotFoundError:
    print("You need to install the stashapi module. (pip install stashapp-tools)",
          file=sys.stderr)

FRAGMENT = json.loads(sys.stdin.read())
stash = StashInterface(FRAGMENT["server_connection"])

# Tag IDs required so that the "Update Performers" tag can be removed
# Studio ID required so that it can be applied to images
PERFORMER_FRAGMENT = """
id
name
aliases
gender
birthdate
death_date
country
ethnicity
hair_color
eye_color
height_cm
weight
measurements
fake_tits
tattoos
piercings
career_length
url
twitter
instagram
details
tags {
  id
}
stash_ids {
  endpoint
  stash_id
}
image_path
favorite
"""

MEDIA_FRAGMENT = """
id
performers {
    id
}
"""

PERFORMER_FILTER = {"tags": {
    "modifier": "INCLUDES",
    "value": 0
}}

MEDIA_FILTER = {"performers": {
    "modifier": "INCLUDES",
    "value": 0
}}


def main():
    dryrun = FRAGMENT['args']['mode'] == 'dryrun'
    log.info(f"Running in {'dry run' if dryrun else 'update'} mode")

    mergeFromTagID, mergeToTagID = setTagFilters()

    # Step 1, find galleries with performers:
    log.info("Searching for performers...")
    PERFORMER_FILTER["tags"]["value"] = mergeToTagID
    destination = stash.find_performers(
        PERFORMER_FILTER, fragment=PERFORMER_FRAGMENT)

    if (len(destination) != 1):
        log.exit(err="There must be exactly one destination performer")
    destination = destination[0]
    destinationID = destination["id"]

    PERFORMER_FILTER["tags"]["value"] = mergeFromTagID
    source = stash.find_performers(
        PERFORMER_FILTER, fragment=PERFORMER_FRAGMENT)

    if (len(source) == 0):
        log.exit(err="There must be at least one source performer")

    total = len(source)
    log.info(f"Found {total} source performers")

    # TODO Refactor:
    for i, performer in enumerate(source):
        log.progress(i/total)

        imageTotal = 0
        sceneTotal = 0
        galleryTotal = 0

        MEDIA_FILTER["performers"]["value"] = performer["id"]

        image_list = stash.find_images(MEDIA_FILTER, fragment=MEDIA_FRAGMENT)
        scene_list = stash.find_scenes(MEDIA_FILTER, fragment=MEDIA_FRAGMENT)
        gallery_list = stash.find_galleries(
            MEDIA_FILTER, fragment=MEDIA_FRAGMENT)

        # Step 3, set image performers:
        for image in image_list:
            imageId = image["id"]
            performers = []
            for id in image["performers"]:
                if (id not in performers):
                    performers.append(id)
            performers.append(destinationID)

            # Build image update and increment counters:
            updated = False
            update_input = {"id": imageId}
            update_input["performer_ids"] = performers
            if not dryrun:
                stash.update_image(update_input)  # Submit update
            if updated:
                imageTotal += 1

        log.info(
            f"Processed {len(image_list)} image(s) from performer {performer['id']}.")

        for gallery in gallery_list:
            galleryId = gallery["id"]
            performers = []
            for id in gallery["performers"]:
                if (id not in performers):
                    performers.append(id)
            performers.append(destinationID)

            # Build gallery update and increment counters:
            updated = False
            update_input = {"id": galleryId}
            update_input["performer_ids"] = performers
            if not dryrun:
                stash.update_gallery(update_input)  # Submit update
            if updated:
                galleryTotal += 1

        log.info(
            f"Processed {len(gallery_list)} gallery(ies) from performer {performer['id']}.")

        for scene in scene_list:
            sceneId = scene["id"]
            performers = []
            for id in scene["performers"]:
                if (id not in performers):
                    performers.append(id)
            performers.append(destinationID)

            # Build scene update and increment counters:
            updated = False
            update_input = {"id": sceneId}
            update_input["performer_ids"] = performers
            if not dryrun:
                stash.update_scene(update_input)  # Submit update
            if updated:
                sceneTotal += 1

        log.info(
            f"Processed {len(scene_list)} scene(s) from performer {performer['id']}.")

    # Build performer update:
    keys = ["aliases", "gender", "birthdate", "death_date", "country",
            "ethnicity", "hair_color", "eye_color", "height_cm", "weight", 
            "measurements", "fake_tits", "tattoos", "piercings", "career_length", 
            "url", "twitter", "instagram", "details"]

    update_input = {"id": destinationID}
    for key in keys:
        if (key in destination and destination[key] != None):
            update_input[key] = destination[key]
    
    update_input["favorite"] = destination["favorite"]
    update_input["name"] = destination["name"]
    if ("stash_ids" in destination):
        update_input["stash_ids"] = destination["stash_ids"]
    update_input["tag_ids"] = []
    if ("tags" in destination):
        for tag in destination["tags"]:
            if (int(tag) != int(mergeFromTagID) and int(tag) != int(mergeToTagID)):
                update_input["tag_ids"].append(tag["id"])

    for performer in source:
        log.error(f"Performer is {performer}")
        for key in keys:
            if ((key not in update_input or update_input[key] == None) and key in performer and performer[key] != None):
                update_input[key] = performer[key]
        if performer["favorite"]:
            update_input["favorite"] = True
        if (update_input["name"] != performer["name"] and performer["name"] not in update_input["aliases"]):
            update_input["aliases"] += ", " + performer["name"]
        if ("stash_ids" in performer):
            for stashid in performer["stash_ids"]:
                update_input["stash_ids"].append(stashid)
        if ("tags" in performer):
            for tag in performer["tags"]:
                if (tag != mergeFromTagID and tag != mergeToTagID):
                    update_input["tag_ids"].append(tag["id"])
        if not dryrun:
            stash.destroy_performer(int(performer["id"]))
            log.info(f"Performer {performer['id']} destroyed.")
        else:
            log.info(f"Performer {performer['id']} not destroyed.")
    
    if not dryrun:
        stash.update_performer(update_input)
    else:
        log.info("No changes to performer made")

    log.exit("Plugin exited normally.")


def setTagFilters():
    # Default to -1 which will give desired behaviour if tags do not exist
    mergeFromTagID = -1
    try:
        mergeFromTagID = stash.find_tag("Merge From Performer")["id"]
        log.debug(f"Merge From Performer tag ID is {mergeFromTagID}")
    except:
        log.exit(err='"Merge From Performer" tag does not exist, cannot proceed')

    mergeToTagID = -1
    try:
        mergeToTagID = stash.find_tag("Merge Into Performer")["id"]
        log.debug(f"Merge Into Performer tag ID is {mergeToTagID}")
    except:
        log.exit(err='"Merge Into Performer" tag does not exist, cannot proceed')

    return mergeFromTagID, mergeToTagID


if __name__ == '__main__':
    main()
