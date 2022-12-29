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
GALLERY_FRAGMENT = """
id
tags {
    id
}
studio {
    id
}
performers {
    id
}
"""

# Gallery performers returned here rather as well as in the gallery fragment
# because images may have multiple galleries with different performers.
# The same is not done for gallery studio IDs because the image can only have
# one studio ID regardless.
IMAGE_FRAGMENT = """
id
galleries {
    performers {
        id
    }
}
performers {
    id
}
tags {
    id
}
studio {
    id
}
"""

# Filter out any galleries with 0 performers - there will be nothing to add to images
GALLERY_FILTER = {"performer_count": {"modifier": "NOT_EQUALS", "value": 0}}

# Filter all images that are not organized and that have at least 1 of:
# - 0 performers
# - no studio
# - tagged "Update Performers" or any ancestor
# - tagged "Update Studio" or any ancestor
# This filter also includes gallery ids, which will be inserted later.
IMAGE_FILTER = {"galleries": {"value": [], "modifier": "INCLUDES"},
                "AND": {"organized": False, "performer_count": {"modifier": "EQUALS", "value": 0},
                        "OR": {"tags": {"value": [], "modifier": "INCLUDES", "depth": -1},
                               "OR": {"is_missing": "studio"}}}}


def main():
    MODE = FRAGMENT['args']['mode']
    log.info(f"Running in {MODE} mode")

    performerTagID, studioTagID = setTagFilters(MODE)

    # Step 1, find galleries with performers:
    log.info("Searching for galleries...")
    gallery_list = stash.find_galleries(
        GALLERY_FILTER, fragment=GALLERY_FRAGMENT)
    # DEBUG:
    # log.error("First Gallery:")
    # log.error(gallery_list[0])
    # log.exit("Debugging exit")
    total = len(gallery_list)
    log.info(f"Found {total} galleries")
    # Step 2, find images in those galleries with no performers:
    log.info("Searching for images...")
    imagetotal = 0
    imgPerformerTotal = 0
    imgStudioTotal = 0
    # TODO Refactor:
    completedImgs = set()
    for i, gallery in enumerate(gallery_list):
        log.progress(i/total)

        # Determine whether or not to set performers and/or studio from this gallery:
        galSetStudio = setGalleryMetadataFlags(
            gallery=gallery, mode=MODE, performerTagID=performerTagID, studioTagID=studioTagID)[1]

        # Include current gallery in the image filter
        galleryID = gallery["id"]
        IMAGE_FILTER["galleries"]["value"] = [galleryID]
        image_list = stash.find_images(IMAGE_FILTER, fragment=IMAGE_FRAGMENT)
        images = len(image_list)
        imagetotal += images

        # Step 3, set image performers:
        if MODE != "dryrun":
            for image in image_list:
                # Each image falls into multiple cases requiring different actions:
                # - 0 performers -> set performers based on galleries
                # - no studio -> set studio based on gallery if present
                # - tagged "Update Performers" -> set performers based on galleries

                # Don't reprocess images. May save time if many images appear in multiple
                # galleries, but has no effect on result.
                imageId = image["id"]
                if imageId in completedImgs:
                    continue
                completedImgs.add(imageId)

                setPerformers, imgSetStudio = setImageMetadataFlags(
                    image, performerTagID, studioTagID)
                setStudio = galSetStudio and imgSetStudio

                if setPerformers:
                    # Images may belong to multiple galleries, which may or may not have
                    # the same performers. All performers from all galleries will
                    # be added to the image, not just the gallery from the filter.
                    performer_ids = []
                    for imgGallery in image["galleries"]:
                        # Only include this gallery if it also meets criteria
                        if setGalleryMetadataFlags(imgGallery, MODE, performerTagID, studioTagID)[0]:
                            for performer in imgGallery["performers"]:
                                id = performer["id"]
                                if id not in performer_ids:
                                    performer_ids.append(id)

                # Build image update and increment counters:
                update_input = {"id": image["id"]}
                if setPerformers and len(performer_ids) > 0:
                    imgPerformerTotal += 1
                    update_input["performer_ids"] = performer_ids
                if setStudio:
                    imgStudioTotal += 1
                    update_input["studio_id"] = gallery["studio"]["id"]
                stash.update_image(update_input)  # Submit update

            log.info(
                f"Updated {len(image_list)} images from gallery {galleryID}.")

    if MODE == "dryrun":
        # TODO improve dry run functionality, including checking both tagged and normal modes
        log.info(
            f"Found {imagetotal} eligible image(s). No changes were made.")
    else:
        log.info(f"Finished updating {imagetotal} images. Updated performers on {imgPerformerTotal} images and updated studio on {imgStudioTotal} images")

    log.exit("Plugin exited normally.")

# Searches for "Update Performers" and "Update Studio" tags and adds them
# to the gallery and image filters
def setTagFilters(MODE):
    # Default to -1 which will give desired behaviour if tags do not exist
    performerTagID = -1
    try:
        performerTagID = stash.find_tag('Update Performers')["id"]
        log.debug(f"Performer tag ID is {performerTagID}")
    except:
        log.info(
            '"Update Performers" tag does not exist, proceeding without tag filtering for performers')

    studioTagID = -1
    try:
        studioTagID = stash.find_tag('Update Studio')["id"]
        log.debug(f"Studio tag ID is {studioTagID}")
    except:
        log.info(
            '"Update Studio" tag does not exist, proceeding without tag filtering for studios')

    IMAGE_FILTER["AND"]["OR"]["tags"]["value"] = [studioTagID, performerTagID]
    if MODE == "tagged":
        # Only consider galleries with the "Update Performers" and/or "Update Studio" tag
        GALLERY_FILTER["tags"]["value"] = [studioTagID, performerTagID]
        GALLERY_FILTER["tags"]["depth"] = -1  # Include ancestors at any level
        log.info(f"Using gallery filter {GALLERY_FILTER}")

    return performerTagID, studioTagID

# Determines which image attributes to set based on the current mode, gallery attributes, and tags
# Returns a tuple of bools indicating whether performers and studio should be set, respectively


def setGalleryMetadataFlags(gallery: dict, mode, performerTagID, studioTagID):
    setPerformers, setStudio = processTags(
        gallery, performerTagID, studioTagID)

    # Studio will be set based on following criteria:
    # - gallery has studio set AND:
    #   - tagged with "Update Studio" OR
    #   - mode is not "tagged"
    if gallery["studio"] == None:
        setStudio = False
    elif mode != "tagged":
        setStudio = True

    # Performer(s) will be set based on following criteria:
    # - gallery has performer(s) set AND:
    #   - tagged with "Update Performers" OR
    #   - mode is not "tagged"
    if "performers" not in gallery or len(gallery["performers"]) == 0:
        setPerformers = False
    elif mode != "tagged":
        setPerformers = True

    return setPerformers, setStudio

# Returns a tuple of bools indicating whether performers and studio should be set, respectively


def setImageMetadataFlags(image: dict, performerTagID, studioTagID):
    setPerformers, setStudio = processTags(
        image, performerTagID, studioTagID, isGallery=False)

    if image["studio"] == None:
        setStudio = True

    if "performers" not in image or len(image["performers"]) == 0:
        setPerformers = True

    return setPerformers, setStudio

# Checks if "Update Performers" or "Update Studio" tags are set and removes them


def processTags(item, performerTagID, studioTagID, isGallery=True):
    # TODO make more generic by passing list of tag IDs and returning list of bools
    itemID = item["id"]
    tagids = []
    updatePerformers = False
    updateStudio = False
    if item["tags"] == None or len(item["tags"]) == 0:
        return updatePerformers, updateStudio

    for tag in item["tags"]:
        tagid = tag["id"]
        if tagid == performerTagID:
            updatePerformers = True
            continue
        if tagid == studioTagID:
            updateStudio = True
            continue
        tagids.append(tagid)
    update_input = {"id": itemID, "tag_ids": tagids}
    if isGallery:
        stash.update_gallery(update_input)
    else:
        stash.update_image(update_input)
    return updatePerformers, updateStudio


if __name__ == '__main__':
    main()
