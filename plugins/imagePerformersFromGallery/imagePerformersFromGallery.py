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

GALLERY_FRAGMENT = """
id
tags {
    id
}
studio {
    id
}
"""
IMAGE_FRAGMENT = """
id
galleries {
    performers {
        id
    }
}
tags {
    id
}
"""

# Filter out any galleries with 0 performers - there will be nothing to add to images
GALLERY_FILTER = {"performer_count": {"modifier": "NOT_EQUALS", "value": 0}}

# Filter all images that are not organized and that have 0 performers.
# This filter also includes gallery ids, which will be inserted later.
# The "Update Performers" tag can override ignored images.
IMAGE_FILTER = {"galleries": {"value": [], "modifier": "INCLUDES"},
    "AND": {"organized": False, "performer_count": { "modifier": "EQUALS", "value": 0}, 
    "OR": {"tags":{"value": -1, "modifier": "INCLUDES"}}}}


def main():
    MODE = FRAGMENT['args']['mode']
    log.info(f"Running in {MODE} mode")

    update_tag_id = -1
    try:
        update_tag_id = stash.find_tag('Update Performers')["id"]
        log.error(f"Tag ID is {update_tag_id}")
        IMAGE_FILTER["AND"]["OR"]["tags"]["value"] = update_tag_id
        if MODE == "tagged":
            # Only consider galleries with the "Update Performers" tag
            GALLERY_FILTER["tags"] = {"value": update_tag_id, "modifier": "INCLUDES"}
            log.info(f"Using gallery filter {GALLERY_FILTER}")
    except:
        log.info('"Update Performers" tag does not exist, proceeding without tag filtering')


    # Step 1, find galleries with performers:
    log.info("Searching for galleries...")
    gallery_list = stash.find_galleries(
        GALLERY_FILTER, fragment=GALLERY_FRAGMENT)
    #DEBUG:
    # log.error("First Gallery:")
    # log.error(gallery_list[0])
    # log.exit("Debugging exit")
    total = len(gallery_list)
    log.info(f"Found {total} galleries")
    # Step 2, find images in those galleries with no performers:
    log.info("Searching for images...")
    imagetotal = 0
    for i, gallery in enumerate(gallery_list):
        log.progress(i/total)
        galleryID = gallery["id"]
        setStudio = False
        if gallery["studio"] != None:
            setStudio = True
            studioID = gallery["studio"]["id"]
        # Include current gallery in the image filter
        IMAGE_FILTER["galleries"]["value"] = [galleryID]
        image_list = stash.find_images(IMAGE_FILTER, fragment=IMAGE_FRAGMENT)
        images = len(image_list)
        imagetotal += images

        # Step 3, set image performers:
        if MODE != "dryrun":
            for image in image_list:
                performer_ids = []
                # Images may belong to multiple galleries, which may or may not have
                # the same performers. All performers from all galleries will
                # be added to the image, not just the gallery from the filter.
                for imgGallery in image["galleries"]:
                    for performer in imgGallery["performers"]:
                        id = performer["id"]
                        if id not in performer_ids:
                            performer_ids.append(id)
                
                # Get the tag ids for the image so that the Update tag can be removed
                tagids = []
                for tag in image["tags"]:
                    tagid = tag["id"]
                    if tagid == update_tag_id:
                        continue # Remove update tag after image is processed
                    tagids.append(tagid)

                update_input = {"id": image["id"],
                                "performer_ids": performer_ids,
                                "tag_ids": tagids}
                if setStudio:
                    update_input["studio_id"] = studioID
                stash.update_image(update_input) # Save performers and tags
            log.info(
                f"Updated {len(image_list)} images from gallery {galleryID}.")

        # Step 4, remove Update tag from gallery:
        tagids = []
        for tag in gallery["tags"]:
            tagid = tag["id"]
            if tagid == update_tag_id:
                continue
            tagids.append(tagid)
        update_input = {"id": galleryID, "tag_ids": tagids}
        stash.update_gallery(update_input)

    if MODE == "dryrun":
        log.info(f"Found {imagetotal} eligible image(s). No changes were made.")
    else:
        log.info(f"Finished updating {imagetotal} images.")

    log.exit("Plugin exited normally.")


if __name__ == '__main__':
    main()
