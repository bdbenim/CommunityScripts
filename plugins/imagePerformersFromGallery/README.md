# Image Performers From Gallery

This plugin sets image performers to match their gallery metadata without modifying already organized images.

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