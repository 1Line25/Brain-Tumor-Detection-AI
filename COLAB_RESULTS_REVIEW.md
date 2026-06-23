# Colab Tuned Model Results Review

Date: 2026-06-21

Test set: 1,994 images.

## Overall comparison

| Model | Validation accuracy | Validation macro F1 | Test accuracy | Test macro F1 |
|---|---:|---:|---:|---:|
| CNN Baseline (old) | 97.76% | 97.74% | **90.92%** | **90.62%** |
| CNN Tuned | 85.71% | 85.94% | 74.97% | 74.38% |
| EfficientNetB0 (old) | 83.71% | 83.68% | 79.79% | 79.72% |
| EfficientNetB0 Tuned | 92.38% | 92.49% | 88.62% | 88.54% |

## Tuned EfficientNet stage selection

| Stage | Validation accuracy | Validation macro F1 | Validation loss |
|---|---:|---:|---:|
| Stage 1: frozen backbone | 91.09% | 91.13% | 0.2264 |
| Stage 2a: last 20 layers | 91.91% | 92.03% | 0.2102 |
| Stage 2b: last 80 layers | **92.38%** | **92.49%** | **0.2044** |

Progressive fine-tuning improved every validation metric. Stage 2b is the correct tuned EfficientNet checkpoint.

## Test metrics by class

### CNN Baseline (old)

| Class | Precision | Recall | F1 |
|---|---:|---:|---:|
| Glioma | 98.90% | 71.80% | 83.20% |
| Meningioma | 89.20% | 93.01% | 91.06% |
| No tumor | 87.50% | 99.80% | 93.25% |
| Pituitary | 90.93% | 99.37% | 94.96% |

### CNN Tuned

| Class | Precision | Recall | F1 |
|---|---:|---:|---:|
| Glioma | 68.50% | 64.80% | 66.60% |
| Meningioma | 77.78% | 55.73% | 64.93% |
| No tumor | 71.87% | 97.62% | 82.79% |
| Pituitary | 83.91% | 82.49% | 83.19% |

Increasing the CNN Glioma class weight did not improve Glioma recall and reduced generalization across all tumor classes. This checkpoint should be rejected.

### EfficientNetB0 (old)

| Class | Precision | Recall | F1 |
|---|---:|---:|---:|
| Glioma | 66.83% | 82.60% | 73.88% |
| Meningioma | 85.32% | 59.81% | 70.32% |
| No tumor | 78.90% | 96.24% | 86.71% |
| Pituitary | 96.24% | 81.01% | 87.97% |

### EfficientNetB0 Tuned

| Class | Precision | Recall | F1 |
|---|---:|---:|---:|
| Glioma | 88.11% | 75.60% | 81.38% |
| Meningioma | 82.46% | 85.83% | 84.11% |
| No tumor | 92.34% | 95.45% | 93.87% |
| Pituitary | 91.72% | 98.10% | 94.80% |

Tuning fixed the old EfficientNet tendency to over-predict Glioma. Test accuracy improved from 79.79% to 88.62%, and macro F1 improved from 79.72% to 88.54%.

## Recommendation

1. Keep `best_cnn_model.h5` as the primary model for highest overall accuracy and macro F1.
2. Reject the tuned CNN checkpoint.
3. Keep `best_tl_tuned_model.h5` as the strongest transfer-learning model and as an alternative when Glioma recall is prioritized.
4. CNN Baseline misses 141 of 500 Glioma cases; EfficientNet Tuned misses 122. EfficientNet catches 19 additional Glioma cases but produces more Glioma false positives.
5. Do not change model weights using the test set. Any threshold calibration or ensemble must be selected using validation data only.

## Artifacts

- `colab_tuned_results_20260621/model_tuned_test_results.json`
- `colab_tuned_results_20260621/tl_stage_validation_metrics.json`
- `colab_tuned_results_20260621/model_tuned_confusion_matrices.png`
- `colab_tuned_results_20260621/model_cnn_tuned_history.png`
- `colab_tuned_results_20260621/model_tl_tuned_history.png`
- `colab_tuned_results_20260621/model_tuned_comparison.png`
