# Image Performers From Gallery

This plugin sets image performers and studio to match their gallery metadata without modifying already organized images.

# Requirements

- Stash (tested on v18.0)
- Python 3 (tested on 3.10.8)
- stashapi module (`pip install stashapp-tools`)

# Usage

## 'All Galleries' Task

Any images that already have 1 or more performers will be ignored, even if their gallery
has more performers, since these are assumed to be already organized. This can be
overridden by creating a tag called "Update Performers" and applying it to images that
you want to force an update on.

## 'Tagged Galleries' Task

Changes can be limited to specific galleries by applying the same "Update Performers"
tag to them and running the "Tagged Galleries" task. Images not in these galleries
will be ignored (even if they also have the "Update Performers" tag)

## 'Dry Run' Task

Running this task performs only the searching for galleries and images without making
any changes. The number of images matching the criteria can be found in the stash logs.
Currently this only corresponds to the 'All Galleries' task, so does not reflect what will
happen when running the 'Tagged Galleries' task.

# Note

Currently the plugin only checks for images based on their number of performers. This means
that images with performers but no studio set will not have their studio added unless the
"Update Performers" tag is applied. It also means that images with 0 performers will have
their studio set to match their gallery, even if this is not desired. For images belonging
to more than one gallery, the gallery used to determine the image studio will depend on which
was returned first by the GraphQL API and is therefore undefined. Better logic to control this
will come in a future update, as well as more control over what gets set by the plugin.