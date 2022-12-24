import json
import sys

try:
    import stashapi.log as log
    from stashapi.stashapp import StashInterface
except ModuleNotFoundError:
    print("You need to install the stashapi module. (pip install stashapp-tools)",
          file=sys.stderr)

FRAGMENT = json.loads(sys.stdin.read())
MODE = FRAGMENT['args']['mode']
stash = StashInterface(FRAGMENT["server_connection"])

GALLERY_FRAGMENT = "id"
IMAGE_FRAGMENT = """
id
galleries {
    performers {
        id
    }
}
"""

# Filter out any galleries with 0 performers - there will be nothing to add to images
GALLERY_FILTER = {"performer_count": {"modifier": "NOT_EQUALS", "value": 0}}

# Filter all images that are not organized and that have 0 performers.
# This filter also includes gallery ids, which will be inserted later.
IMAGE_FILTER = {"organized": False, "performer_count": {
    "modifier": "EQUALS", "value": 0}, "galleries": {"value": [], "modifier": "INCLUDES"}}


def main():
    log.info(f"Running in mode {MODE}")

    # Step 1, find galleries with performers:
    log.info("Searching for galleries...")
    gallery_list = stash.find_galleries(
        GALLERY_FILTER, fragment=GALLERY_FRAGMENT)
    total = len(gallery_list)
    log.info(f"Found {total} galleries")
    # Step 2, find images in those galleries with no performers:
    log.info("Searching for images...")
    imagetotal = 0
    for i, gallery in enumerate(gallery_list):
        log.progress(i/total)
        galleryID = gallery["id"]
        IMAGE_FILTER["galleries"]["value"] = [galleryID] # Include current gallery in the image filter
        image_list = stash.find_images(IMAGE_FILTER, fragment=IMAGE_FRAGMENT)
        images = len(image_list)
        imagetotal += images

        # Step 3, set image performers:
        if MODE == "update":
            for image in image_list:
                performer_ids = []
                # Images may belong to multiple galleries, which may or may not have
                # the same performers. All performers from all galleries will
                # be added to the image, not just the gallery from the filter.
                for gallery in image["galleries"]:
                    for performer in gallery["performers"]:
                        id = performer["id"]
                        if id not in performer_ids:
                            performer_ids.append(id)

                update_input = {"id": image["id"], "performer_ids": performer_ids}
                stash.update_image(update_input)
            log.info(f"Updated {len(image_list)} images from gallery {galleryID}.")

    if MODE == "update":
        log.info(f"Finished updating {imagetotal} images.")
    elif MODE == "dryrun":
        log.info(f"Found {imagetotal} eligible images. No changes were made.")

    log.exit("Plugin exited normally.")


if __name__ == '__main__':
    main()
