# Google Colab GPU Training Guide

This guide runs the project on Colab GPU while saving model checkpoints directly to Google Drive.

## 1. Create a bundle on Windows

Run this command from the project folder in PowerShell:

```powershell
tar -a -c -f brain_tumor_colab.zip data 02_Preprocessing_v2.ipynb 03_Model_v3.ipynb class_mapping.json class_mapping.csv
```

Upload `brain_tumor_colab.zip` to:

```text
Google Drive/MyDrive/BrainTumor/brain_tumor_colab.zip
```

## 2. Enable a Colab GPU

In Colab, choose:

```text
Runtime > Change runtime type > Hardware accelerator > T4 GPU
```

Run this cell to verify the GPU:

```python
import tensorflow as tf

print(tf.__version__)
print(tf.config.list_physical_devices('GPU'))
```

The GPU list must not be empty.

## 3. Mount Google Drive

```python
from google.colab import drive
drive.mount('/content/drive')
```

## 4. Extract the project to fast Colab storage

Keep training images in `/content`, not Google Drive, because reading thousands of small files directly from Drive is slow.

```python
import os
import shutil
from pathlib import Path

ZIP_PATH = Path('/content/drive/MyDrive/BrainTumor/brain_tumor_colab.zip')
PROJECT_DIR = Path('/content/brain_tumor_project')
CHECKPOINT_DIR = Path('/content/drive/MyDrive/BrainTumor/checkpoints')

if PROJECT_DIR.exists():
    shutil.rmtree(PROJECT_DIR)

PROJECT_DIR.mkdir(parents=True)
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
shutil.unpack_archive(str(ZIP_PATH), str(PROJECT_DIR))
os.chdir(PROJECT_DIR)

print('Project:', Path.cwd())
print('Checkpoints:', CHECKPOINT_DIR)
```

## 5. Install the small missing dependencies

Do not upgrade TensorFlow unless the notebook reports a real compatibility error.

```python
!pip install -q opencv-python-headless pandas scikit-learn seaborn
```

## 6. Run preprocessing on Colab

The CSV files currently contain Windows paths, so preprocessing must run once in Colab to create valid Linux paths.

### Recommended: run with visible progress

`nbconvert` captures output from the child notebook, which can make preprocessing look frozen while it is processing more than 10,000 images. Use this runner to display each cell and the `processed 500/...` progress messages immediately:

```python
import json
from pathlib import Path

notebook = json.loads(Path('02_Preprocessing_v2.ipynb').read_text(encoding='utf-8'))
namespace = {'__name__': '__main__'}

for cell_index, cell in enumerate(notebook['cells']):
    if cell.get('cell_type') != 'code':
        continue

    print(f'\n===== Running preprocessing cell {cell_index} =====', flush=True)
    source = ''.join(cell.get('source', []))
    exec(compile(source, f'02_Preprocessing_v2.ipynb cell {cell_index}', 'exec'), namespace)

print('\nPreprocessing completed.', flush=True)
```

The preprocessing code is resumable: existing files are skipped when `FORCE_REPROCESS=False`. Stopping an apparently frozen `nbconvert` cell does not delete images that were already written.

### Alternative: execute with nbconvert

```python
!jupyter nbconvert \
  --to notebook \
  --execute 02_Preprocessing_v2.ipynb \
  --output 02_Preprocessing_v2_colab_run.ipynb \
  --ExecutePreprocessor.timeout=-1
```

This method may show no new output for several minutes. Completion is indicated by a final `Writing ... to 02_Preprocessing_v2_colab_run.ipynb` message.

Verify the generated files:

```python
from pathlib import Path

for name in ['df_train.csv', 'df_val.csv', 'df_test.csv']:
    print(name, Path(name).exists())

print('Processed images:', len(list(Path('data_processed_roi').rglob('*.png'))))
```

## 7. Save checkpoints directly to Drive

`03_Model_v3.ipynb` reads this environment variable:

```python
import os

os.environ['MODEL_OUTPUT_DIR'] = str(CHECKPOINT_DIR)
print(os.environ['MODEL_OUTPUT_DIR'])
```

## 8. Train both tuned models

```python
!jupyter nbconvert \
  --to notebook \
  --execute 03_Model_v3.ipynb \
  --output 03_Model_v3_colab_run.ipynb \
  --ExecutePreprocessor.timeout=-1
```

The notebook trains:

1. CNN with a 20% Glioma weight increase.
2. EfficientNet Stage 1 with a frozen backbone.
3. EfficientNet Stage 2a with the last 20 non-BN layers unfrozen.
4. EfficientNet Stage 2b with the last 80 non-BN layers unfrozen and a lower learning rate.
5. Global EfficientNet checkpoint selection by validation macro F1.
6. Final test evaluation and confusion matrices.

## 9. Copy executed notebooks and reports to Drive

Checkpoints are already written directly to Drive. Copy the executed notebooks as well:

```python
import shutil

for name in [
    '02_Preprocessing_v2_colab_run.ipynb',
    '03_Model_v3_colab_run.ipynb',
]:
    src = PROJECT_DIR / name
    if src.exists():
        shutil.copy2(src, CHECKPOINT_DIR / name)

print('\nSaved outputs:')
for path in sorted(CHECKPOINT_DIR.iterdir()):
    print(path.name)
```

Expected important files:

```text
best_cnn_tuned_model.h5
best_tl_stage1_model.h5
best_tl_stage2a_model.h5
best_tl_stage2b_model.h5
best_tl_tuned_model.h5
tl_stage_validation_metrics.json
model_tuned_test_results.json
model_tuned_confusion_matrices.png
```

## 10. Resume after a disconnected runtime

The completed checkpoints remain in Google Drive. Reconnect, repeat steps 2-7, then either rerun the full model notebook or load the saved checkpoint needed for evaluation.

Do not use `best_cnn_tuned_incomplete.h5`; it came from the interrupted native-Windows CPU run and had not converged.

## 11. Share Colab results back for local review

The reviewer cannot directly access the Colab runtime or Google Drive. Create a small ZIP containing metrics and plots (models are intentionally excluded because H5 checkpoints are large):

```python
import zipfile
from pathlib import Path

result_names = [
    'tl_stage_validation_metrics.json',
    'model_tuned_test_results.json',
    'model_tuned_confusion_matrices.png',
    'model_tuned_comparison.png',
    'model_cnn_tuned_history.png',
    'model_tl_tuned_history.png',
]

result_zip = CHECKPOINT_DIR / 'model_tuned_results.zip'
with zipfile.ZipFile(result_zip, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in result_names:
        path = CHECKPOINT_DIR / name
        if path.exists():
            archive.write(path, arcname=name)
            print('Added:', name)
        else:
            print('Missing:', name)

print('Created:', result_zip)
```

Download it from Colab:

```python
from google.colab import files
files.download(str(result_zip))
```

Place `model_tuned_results.zip` in the local project root. The metrics and plots can then be extracted and reviewed locally. H5 checkpoints only need to be downloaded later when local inference or deployment testing is required.

## 12. Run the deep evaluation notebook

Upload the updated local `04_Evaluation_v2.ipynb` into the current Colab project directory. The simplest upload cell is:

```python
from google.colab import files
uploaded = files.upload()  # Select 04_Evaluation_v2.ipynb
```

Select the tuned EfficientNet checkpoint and a persistent Drive output directory:

```python
import os

EVAL_DIR = CHECKPOINT_DIR / 'evaluation_effnet_tuned'
EVAL_DIR.mkdir(parents=True, exist_ok=True)

os.environ['EVAL_MODEL_PATH'] = str(CHECKPOINT_DIR / 'best_tl_tuned_model.h5')
os.environ['EVAL_MODEL_NAME'] = 'EfficientNetB0 Tuned'
os.environ['EVAL_OUTPUT_DIR'] = str(EVAL_DIR)

print('Model exists:', Path(os.environ['EVAL_MODEL_PATH']).exists())
print('Evaluation output:', EVAL_DIR)
```

Run Evaluation 04 with visible cell progress:

```python
import json
from pathlib import Path

notebook = json.loads(Path('04_Evaluation_v2.ipynb').read_text(encoding='utf-8'))
namespace = {'__name__': '__main__'}

for cell_index, cell in enumerate(notebook['cells']):
    if cell.get('cell_type') != 'code':
        continue

    print(f'\n===== Running evaluation cell {cell_index} =====', flush=True)
    source = ''.join(cell.get('source', []))
    exec(compile(source, f'04_Evaluation_v2.ipynb cell {cell_index}', 'exec'), namespace)

print('\nEvaluation completed.', flush=True)
```

Expected outputs in `Google Drive/MyDrive/BrainTumor/checkpoints/evaluation_effnet_tuned`:

```text
evaluation_metrics.json
classification_report.txt
eval_metrics_by_class.png
eval_confusion_matrix.png
eval_roc_curve.png
eval_gradcam.png
eval_wrong_predictions.png
eval_summary_dashboard.png
```

Package these reports for local review:

```python
import shutil

archive_path = shutil.make_archive(
    str(CHECKPOINT_DIR / 'evaluation_effnet_tuned'),
    'zip',
    root_dir=EVAL_DIR,
)
print('Created:', archive_path)

from google.colab import files
files.download(archive_path)
```
