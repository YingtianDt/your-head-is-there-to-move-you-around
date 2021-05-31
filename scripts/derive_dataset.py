from loaders import utils, pvc4

import argparse
import collections
import glob
import matplotlib
import matplotlib.image
import numpy as np
import os
import pandas as pd
import scipy
import scipy.signal
import shutil
import tables

import sys

sys.path.append("../")
from paths import *


def copytree(src, dst, symlinks=False, ignore=None):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)


def derive_pvc1(args):
    root = f"{args.data_root}/crcns-pvc1"
    movie_info = {}

    out_path = f"{args.output_dir}/crcns-pvc1"
    try:
        os.makedirs(out_path)
    except FileExistsError:
        pass

    h5file = tables.open_file(f"{out_path}/movies.h5", "w")

    # Crop and downsample the frames to 112x112. This reduces the
    # interlacing artifacts
    for i in range(30):
        for j in range(4):
            print(i, j)
            root_ = os.path.join(root, "movie_frames", f"movie{j:03}_{i:03}.images")
            with open(os.path.join(root_, "nframes"), "r") as f:
                nframes = int(f.read())

                ims = []
                for frame in range(nframes):
                    im_name = f"movie{j:03}_{i:03}_{frame:03}.jpeg"
                    the_im = matplotlib.image.imread(os.path.join(root_, im_name))

                    assert the_im.shape[0] == 240
                    the_im = the_im.reshape((120, 2, 160, 2, 3)).mean(3).mean(1)
                    the_im = the_im[8:, 24:136, :].transpose((2, 0, 1))
                    ims.append(the_im.astype(np.uint8))

                m = np.stack(ims, axis=0)
                h5file.create_array("/", f"movie{j:03}_{i:03}", m, "Movie")

    h5file.close()

    os.system(f'cp -r "{args.data_root}/crcns-pvc1/neurodata" "{out_path}"')


def derive_pvc4(args):
    framerate = 72
    min_seconds = 60  # At least one minute of data

    root = os.path.join(args.data_root, "crcns-pvc4")
    paths = []
    for item in glob.glob(os.path.join(root, "Nat", "*", "*summary_file.mat")):
        paths.append(item)

    for item in glob.glob(os.path.join(root, "NatRev", "*", "*summary_file.mat")):
        paths.append(item)

    paths = sorted(paths)

    images = []
    cells = []
    spktimes = []

    cell_info = collections.OrderedDict()
    i = 0
    for path in paths:
        summary = utils.load_mat_as_dict(path)

        respfiles = summary["celldata"]["respfile"]
        stimfiles = summary["celldata"]["stimfile"]
        cellids = summary["celldata"]["cellid"]
        repcounts = summary["celldata"]["repcount"]

        if not isinstance(respfiles, list):
            respfiles = [respfiles]
            stimfiles = [stimfiles]
            cellids = [cellids]
            repcounts = [repcounts]

        for respfile, stimfile, cellid, repcount in zip(
            respfiles, stimfiles, cellids, repcounts
        ):
            assert "+" not in respfile
            resppath = os.path.join(os.path.dirname(path), respfile)

            stimpath = os.path.join(os.path.dirname(path), stimfile)

            try:
                framecount, iconsize, iconside, filetype = pvc4._openimfile(stimpath)
            except FileNotFoundError:
                continue

            if iconside < 60:
                continue

            info = {
                "cellid": cellid,
                "nrepeats": repcount,
                "stimpath": stimpath,
                "resppath": resppath,
                "summarypath": path,
                "framecount": framecount,
            }

            if cellid not in cell_info:
                cell_info[cellid] = [info]
            else:
                cell_info[cellid].append(info)

            i += 1

    for key, val in cell_info.items():
        if "e0030" in val[0]["summarypath"]:
            # Too short
            continue

        if "r0336" in val[0]["summarypath"]:
            # The image file is truncated
            continue

        if "r0056" in val[0]["summarypath"]:
            # Too many nans
            continue

        if "e0101" in val[0]["summarypath"]:
            # Not enough data
            continue

        ntraining_frames = sum([x["framecount"] for x in val])
        if ntraining_frames < framerate * min_seconds:
            continue

        out_path = os.path.join(
            args.output_dir,
            "crcns-pvc4",
            "/".join(val[0]["summarypath"].split("/")[-3:-1]),
        )

        os.makedirs(out_path)

        # Copy over the summary file
        os.system(f'cp "{val[0]["summarypath"]}" "{out_path}"')

        for it in val:
            if "e0113.edrev3.003.p1" in it["stimpath"]:
                # There's an issue with this mat file
                continue

            os.system(f'cp "{it["stimpath"]}" "{out_path}"')
            os.system(f'cp "{it["resppath"]}" "{out_path}"')


def main(args):
    try:
        os.makedirs(args.output_dir)
    except FileExistsError:
        pass

    if args.dataset == "pvc1":
        derive_pvc1(args)
    elif args.dataset == "pvc4":
        derive_pvc4(args)
    else:
        raise NotImplementedError(f"dataset '{args.dataset}' Not implemented")


if __name__ == "__main__":

    desc = "Derive a dataset"
    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument("--dataset", help="Dataset")
    parser.add_argument("--data_root", default=RAW_DATA, help="Data path")
    parser.add_argument("--output_dir", default=DERIVED_DATA, help="Output path")

    args = parser.parse_args()
    main(args)
