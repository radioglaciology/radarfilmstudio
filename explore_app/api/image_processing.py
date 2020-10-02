import os
import time
from io import BytesIO
import requests

from PIL import Image, ImageOps


OVERLAP_FACTOR = 88 / 11362  # Overlap between adjacent radargram images as a percentage of the width of the image


def worker_load_image(filename, film_images_dir):
    if "https://" in film_images_dir:
        response = requests.get(film_images_dir + filename)
        return Image.open(BytesIO(response.content))
    else:
        return Image.open(os.path.join(film_images_dir, filename))


def stitch_images(img_paths, image_type, flip, scale_x, scale_y, qid, output_dir, film_images_dir):
    print(f'Starting stitch with qid {qid}')

    images = []  # TODO: This needs to move to a separate thread!
    sum_x = 0
    for img_path in img_paths:
        if image_type == 'jpg':
            pre, ext = os.path.splitext(img_path)
            img_path = pre + "_lowqual.jpg"
            filename_out = f"stitch-{qid}.png"
        else:  # otherwise assume TIFF
            filename_out = f"stitch-{qid}.tiff"

        im = worker_load_image(img_path, film_images_dir)
        if flip == 'x':
            im = ImageOps.mirror(im)

        if image_type == 'jpg':
            im = im.resize((round(im.size[0] * scale_x), round(im.size[1] * scale_y)))
        else:
            im = im.resize((round(im.size[0] * scale_x), round(im.size[1] * scale_y)), resample=Image.NEAREST)

        images.append(im)
        sum_x += im.width

    overlap_px = int(images[0].width * OVERLAP_FACTOR)

    im_output = Image.new(images[0].mode, (sum_x - (overlap_px * (len(images) - 1)), images[0].height))

    x = 0
    for im in images:
        im_output.paste(im.crop((int(overlap_px / 2), 0, im.width, im.height)), (x + int(overlap_px / 2), 0))
        x += im.width - overlap_px

    if flip == 'x':
        im_output = ImageOps.mirror(im_output)

    im_output.save(os.path.join(output_dir, filename_out))

    print(f"Completed stitch at {time.time()}")

    return {
        'filename': filename_out,
        'timestamp': time.time()
    }