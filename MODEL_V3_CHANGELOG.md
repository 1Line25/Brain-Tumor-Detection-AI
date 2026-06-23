# Model V3 Tuning Log

## 2026-06-21 - Planned tuning pass

Baseline test results before this change (1,994 images):

| Model | Accuracy | Macro Precision | Macro Recall | Macro F1 |
|---|---:|---:|---:|---:|
| CNN Baseline | 90.92% | 91.63% | 90.99% | 90.62% |
| EfficientNetB0 TL | 79.79% | 81.82% | 79.91% | 79.72% |

Planned changes:

1. Preserve old checkpoints and write tuned checkpoints under new names.
2. Synchronize Model 03 augmentation with the conservative MRI augmentation from preprocessing.
3. Increase the CNN Glioma loss weight by 20% because CNN Glioma precision is high (98.90%) but recall is low (71.80%).
4. Monitor validation macro F1 in addition to accuracy.
5. Simplify the EfficientNet classification head.
6. Save separate EfficientNet checkpoints for Stage 1, Stage 2a, and Stage 2b.
7. Reduce learning rate when progressively unfreezing more EfficientNet layers.
8. Select the final EfficientNet checkpoint by validation macro F1 rather than allowing later stages to overwrite earlier best models.

Files expected after training:

- `best_cnn_tuned_model.h5`
- `best_tl_stage1_model.h5`
- `best_tl_stage2a_model.h5`
- `best_tl_stage2b_model.h5`
- `best_tl_tuned_model.h5`
- `model_tuned_test_results.json`
- `model_tuned_confusion_matrices.png`

## Run results

Colab training and evaluation completed. See `COLAB_RESULTS_REVIEW.md`.

Final recommendation:

- Primary model: existing `best_cnn_model.h5` (test accuracy 90.92%, macro F1 90.62%).
- Best transfer model: `best_tl_tuned_model.h5` (test accuracy 88.62%, macro F1 88.54%).
- Rejected experiment: CNN with 20% Glioma weight increase (test accuracy 74.97%, macro F1 74.38%).

## 2026-06-21 - Implemented notebook changes

- Backed up the original notebook as `03_Model_v3_before_tuning.ipynb`.
- Updated `03_Model_v3.ipynb` with the planned tuning changes.
- Added validation macro F1 as the checkpoint selection metric.
- Added a 20% Glioma weight multiplier for the tuned CNN only.
- Preserved frequency-balanced weights for EfficientNet.
- Added conservative MRI augmentation matching preprocessing.
- Added separate EfficientNet stage checkpoints and global stage selection.
- Added final test metrics, classification reports, and confusion-matrix generation.
- Cleared old notebook outputs so old and tuned results cannot be confused.

## 2026-06-21 - Native Windows CPU training attempt

The full retraining attempt was stopped by the 30-minute execution limit:

| Epoch | Train accuracy | Validation accuracy | Validation macro F1 | Time |
|---:|---:|---:|---:|---:|
| 1 | 63.47% | 31.35% | 19.02% | 643 s |
| 2 | 78.45% | 47.58% | 31.44% | 630 s |

The checkpoint had not converged and was renamed to `best_cnn_tuned_incomplete.h5`; it must not be compared with completed models. TensorFlow 2.21 on native Windows is using CPU only, and one CNN epoch takes roughly 10.5 minutes on this machine.

To provide an immediate valid result without selecting hyperparameters on the test set, the next experiment uses class-probability calibration:

1. Tune a Glioma probability multiplier on the validation set only.
2. Freeze that multiplier.
3. Evaluate once on the test set.
4. Save calibration parameters, metrics, and confusion matrices.

## 2026-06-21 - Colab portability update

- Added `MODEL_OUTPUT_DIR` support to `03_Model_v3.ipynb`.
- Local runs continue to save outputs in the project directory.
- Colab can set `MODEL_OUTPUT_DIR` to a Google Drive checkpoint folder while keeping image data in fast `/content` storage.
- This prevents completed checkpoints from being lost when a Colab runtime disconnects.
- Added `COLAB_TRAINING_GUIDE.md` with the complete upload, GPU, preprocessing, training, and result-download workflow.
- Added a visible-progress preprocessing runner because `nbconvert` captures child-notebook output and can appear frozen while processing images.
- Added a result-packaging step so Colab metrics and plots can be downloaded as `model_tuned_results.zip` for local review without transferring large H5 checkpoints.
- Prepared the portable Evaluation 04 workflow; details are recorded in `EVALUATION_V2_CHANGELOG.md` and the Colab guide.
