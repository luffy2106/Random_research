import sys
import time
import os
import logging

from pathlib import Path

from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.pdftypes import resolve1

from os import listdir, remove, mkdir, rename
from os.path import isfile, join, basename, isdir
from pdf2image import convert_from_path
from subprocess import check_output
from shutil import copy, rmtree
from re import search


# set up logging
logger = logging.getLogger("Split Image")
logger.setLevel(logging.INFO)
format_string = "%(asctime)s: %(levelname)s: %(message)s"
formatter = logging.Formatter(format_string, datefmt="%Y-%m-%dT%H:%M:%S")
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)


def _pdf_file_name(file_name, number_of_pages):
    for i in range(number_of_pages):
        yield f"{file_name}"


def convert_pdf_image(img_folder, file, nb_pages):
    """
    convert pdf to image. The higher dpi the better resolution, but the time converting also increase
    :param img_folder: path of the target folder where the image pages are generated
    :param file: path of original file
    :return: list of path images page
    """
    imgs = []
    file_name = basename(file)[:-4]
    mkdir(img_folder)
    start_time = time.time()
    logger.info("Begin of the conversion")

    images = convert_from_path(file, dpi=300, thread_count=4)

    images_from_path = convert_from_path(
        file,
        dpi=300,
        output_folder=img_folder,
        output_file=_pdf_file_name(file_name, nb_pages),
        thread_count=4,
        fmt="jpg",
        paths_only=True,
    )

    logger.info("End of the conversion")
    end_time = time.time()
    timer = "Conversion time : {}".format(end_time - start_time)
    logger.info(f"Time of conversion => {timer}")

    return images_from_path


def pdf2png(file, nb_pages, document_pages_image, bi_name):
    """
    3 case:
    1. folder image exist but the number of image is not equal to the number of splitted pdf => delete folder and
    convert pdf to image
    2. folder image exist but the number of image is equal to the number of splitted pdf => take the image which don't
     have string "line" in the folder
    3. folder image is exist =>  convert pdf to image
    """
    logger.info("start working on split image")
    imgs = []
    file_name = basename(file)[:-4]
    img_folder = document_pages_image + "/" + bi_name + "/" + file_name
    if isdir(img_folder):
        logger.info(f"Directory {img_folder} is already existed")
        imgs = [
            img_folder + "/" + f
            for f in listdir(img_folder)
            if isfile(join(img_folder, f)) and "line" not in f
        ]
        if (
            len(imgs) != nb_pages
        ):  # recreate folder of image if number of image is not equal to number of pdf page
            rmtree(img_folder)
            imgs = convert_pdf_image(img_folder, file, nb_pages)
    else:
        imgs = convert_pdf_image(img_folder, file, nb_pages)
    # imgs = [[img, search("-([0-9]+).jpg", img).group(1)] for img in imgs]
    # imgs = sorted(imgs, key=lambda img: int(img[1]))
    # imgs = [img[0] for img in imgs]
    return imgs


def rename_end_files(files):
    files_new_name = []
    for old_name in files:
        if ".." in old_name:
            new_name = old_name.replace("..", ".")
            os.rename(old_name, new_name)
            files_new_name.append(new_name)
        else:
            files_new_name.append(old_name)
    return files_new_name


def split_bi_image(bi_path, image_pages_path, log):
    f_log = open(log, "w")
    for bi in bi_path:
        path_bi = Path(bi).parent
        bi_name = basename(path_bi)
        splitted_bi_path = image_pages_path + bi_name
        if not isdir(splitted_bi_path):
            mkdir(splitted_bi_path)
        list_spdp = [bi + "/" + spdp for spdp in listdir(bi)]
        list_spdp = rename_end_files(list_spdp)
        for spdp in list_spdp:
            with open(spdp, "rb") as f:
                parser = PDFParser(f)
                doc = PDFDocument(parser)
                parser.set_document(doc)
                pages = resolve1(doc.catalog["Pages"])
                pages_count = pages.get("Count", 0)
                logger.info(f"{pages_count} pages on {spdp} file.")
                if pages_count > 500:
                    continue
                try:
                    pdf2png(spdp, pages_count, image_pages_path, bi_name)
                except Exception as e:
                    print(e)
                    logger.error(
                        f"error on convert pdt to image at file :  {basename(spdp)}. \n Error => {e}"
                    )
                    f_log.write(
                        "error on convert pdf to image at file : "
                        + basename(spdp)
                        + " at BI : "
                        + bi_name
                    )
    f_log.close()
    return


log = "./log_image.txt"
image_pages_path = "./image_pages/"
# mkdir(image_pages_path)
# pdf_file = "./V-216B-131-A-871_000_001_01.pdf"
pdf_folder = "./BI"
bi_path = [pdf_folder + "/" + bi + "/SPDP" for bi in os.listdir(pdf_folder)]
split_bi_image(bi_path, image_pages_path, log)
