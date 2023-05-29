# Image Performers From Gallery

This plugin sets image performers and studio to match their gallery metadata without modifying already organized images.

# Requirements

- Stash (tested on v18.0)
- Python 3 (tested on 3.10.8)
- stashapi python module (`pip install stashapp-tools`)

# Usage

## 'All Galleries' Task

The plugin will find all images missing a studio and/or performers in any
gallery, provided the gallery has some or all of that missing data.

Any images that already have 1 or more performers will be ignored, even if their gallery
has more performers, since these are assumed to be already organized. This can be
overridden by creating a tag called "Update Performers" and applying it to images that
you want to force an update on.

Likewise for studios, any images that already have a studio set will be
ignored, even if their gallery has a different studio. This can be overridden in a
similar manner y creating a tag called "Update Studio" and applying it to images that
you want to force an update on.

The tags can be applied in any combination to force one or both elements to be updated.

## 'Tagged Galleries' Task

Changes can be limited to specific galleries by applying the same "Update Performers"
and "Update Studio" tags to them and running the "Tagged Galleries" task. Images not 
in these galleries will be ignored (even if they also have the "Update Performers" tag).

In this mode, studios will only be set for galleries that have the "Update Studio" tag
and performers only for galleries that have the "Update Performers" tag. Just as above,
these tags can be applied in any combination.

## 'Dry Run' Task

Running this task performs only the searching for galleries and images without making
any changes. The number of images matching the criteria can be found in the stash logs.
Currently this only corresponds to the 'All Galleries' task, so does not reflect what will
happen when running the 'Tagged Galleries' task.

# Notes

Currently the plugin only checks for images that meet at least one of the following criteria:

- the image has 0 performers
- the image has no studio
- the image is tagged "Update Performers"
- the image is tagged "Update Studio"

For images belonging to more than one gallery, the gallery used to determine the image's studio
will depend on which was returned first by the GraphQL API and is therefore undefined. Better
logic to control this will come in a future update, as well as more control over what gets set
by the plugin.

The tags described above may also be applied as sub-tags. For instance, an "Update All" tag applied to an
image could satisfy these criteria if it is a parent of the other tags.