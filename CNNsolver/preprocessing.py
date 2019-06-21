#-----------------------------------------------------#
#                   Library imports                   #
#-----------------------------------------------------#
#External libraries
import numpy as np
import math
from keras.utils import to_categorical
#Internal libraries/scripts
from data_io import case_loader, mri_pickle_backup
from utils.matrix_operations import slice_3Dmatrix

#-----------------------------------------------------#
#          Patches and Batches Preprocessing          #
#-----------------------------------------------------#
# Load and preprocess all MRI's to batches for later training or prediction
def preprocessing_MRIs(cases, config, training=False, skip_blanks=False):
    # Parameter initialization
    casePointer = []
    # Iterate over each case
    for i in cases:
        # Load the MRI of the current case
        mri = case_loader(i, config["data_path"],
                          load_seg=training,
                          pickle=False)
        # IF scaling: Scale each volume value to [0,1]
        if config["scale_input_values"]:
            mri.vol_data = scale_volume_values(mri.vol_data)
        # Slice volume into patches
        patches_vol = slice_3Dmatrix(mri.vol_data,
                                     config["patch_size"],
                                     config["overlap"])
        # IF training: Slice segmentation into patches
        if training:
            patches_seg = slice_3Dmatrix(mri.seg_data,
                                         config["patch_size"],
                                         config["overlap"])
            # IF skip blank patches: remove all blank patches from the list
            if skip_blanks:
                patches_vol, patches_seg = remove_blanks(patches_vol,
                                                         patches_seg)
            print(len(patches_vol))
            # IF rotation: Rotate patches for data augmentation
            if config["rotation"]:
                patches_vol, patches_seg = rotate_patches(patches_vol,
                                                          patches_seg)
            # IF reflection: Reflect patches for data augmentation
            if config["reflection"]:
                patches_vol, patches_seg = reflect_patches(patches_vol,
                                                           patches_seg)
            print(len(patches_vol))
        # Calculate the number of batches for this MRI
        steps = math.ceil(len(patches_vol) / config["batch_size"])
        # Create batches from the volume patches
        batches_vol = create_batches(patches_vol,
                                     config["batch_size"],
                                     steps)
        mri.add_batches(batches_vol, vol=True)
        # IF training: Create batches from the segmentation batches
        if training:
            batches_seg = create_batches(patches_seg,
                                         config["batch_size"],
                                         steps)
            # Transform digit segmentation classes into categorical
            for b, batch in enumerate(batches_seg):
                batches_seg[b] = to_categorical(batch,
                                                num_classes=config["classes"])
            mri.add_batches(batches_seg, vol=False)
        # Backup MRI to pickle for faster access in later usages
        mri_pickle_backup(i, mri)
        # Save the number of steps in the casePointer list
        casePointer.extend([i] * steps)
    # Return the casePointer list for the data generator usage later
    return casePointer

# Create batches from a list of patches
def create_batches(patches, batch_size, steps):
    # Initialize result list
    batches = []
    # Create a batch in each step
    for i in range(0, steps):
        # Assign patches to the next batch
        start = i * batch_size
        end = start + batch_size
        if end > len(patches):
            end = len(patches)
        # Concatenate volume patches into the batch
        batch = np.concatenate(patches[start:end], axis=0)
        # Append batch to result batches list
        batches.append(batch)
    # Return resulting batches list
    return batches

#-----------------------------------------------------#
#            Other preprocessing functions            #
#-----------------------------------------------------#
# Remove all blank patches (with only background)
def remove_blanks(patches_vol, patches_seg, background_class=0):
    # Iterate over each patch
    for i in reversed(range(0, len(patches_seg))):
        # IF patch DON'T contain any non background class -> remove it
        if not np.any(patches_seg[i] != background_class):
            del patches_vol[i]
            del patches_seg[i]
    # Return all non blank patches
    return patches_vol, patches_seg

# Scale the input volume voxel values between [0,1]
def scale_volume_values(volume):
    # Identify minimum and maximum
    max_value = np.max(volume)
    min_value = np.min(volume)
    # Scaling
    volume_normalized = (volume - min_value) / (max_value - min_value)
    # Return scaled volume
    return volume_normalized

# Rotate patches at the y-z axis
def rotate_patches(patches_vol, patches_seg):
    # Initialize lists for rotated patches
    rotated_vol = []
    rotated_seg = []
    # Iterate over 90,180,270 degree (1*90, 2*90, 3*90)
    for times in range(1,4):
        # Iterate over each patch
        for i in range(len(patches_vol)):
            # Rotate volume & segmentation and cache rotated patches
            patch_vol_rotated = np.rot90(patches_vol[i], k=times, axes=(2,3))
            rotated_vol.append(patch_vol_rotated)
            patch_seg_rotated = np.rot90(patches_seg[i], k=times, axes=(2,3))
            rotated_seg.append(patch_seg_rotated)
    # Add rotated patches to the original patches lists
    patches_vol.extend(rotated_vol)
    patches_seg.extend(rotated_seg)
    # Return processed patches lists
    return patches_vol, patches_seg

def reflect_patches(patches_vol, patches_seg):
    return patches_vol, patches_seg
