# Blank Page Detection - Parameter Optimization Tools

This directory contains tools for data-driven optimization of blank page detection parameters. Instead of manually trying different parameter combinations, these tools analyze your actual medical report PDFs to determine optimal thresholds.

## Problem Statement

The blank page detection system uses three criteria to identify blank pages:
- **Variance threshold**: Low variance indicates uniform (blank) pages
- **Edge threshold**: Few edges suggest minimal content
- **White pixel ratio**: High proportion of white pixels indicates blank pages

Finding the right thresholds manually through trial and error is time-consuming and ineffective. These tools provide a systematic, data-driven approach.

## Solution Overview

The toolkit consists of six integrated tools that work together:

1. **Sample Extraction Tool** - Extracts and labels sample pages from your PDFs
2. **Automated Parameter Optimizer** - Analyzes samples to find optimal thresholds
3. **Interactive Parameter Tuner** - Visual tool for fine-tuning parameters
4. **Parameter Validation Script** - Tests and compares configurations
5. **Config Runner** - Run processing with different configs without modifying main config
6. **Config Manager** - Deploy, backup, and restore configurations safely

## Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Extract Samples                                             │
│  python tools/extract_samples.py --pdf input/reports.pdf        │
│  → Creates labeled dataset: samples/blank/, samples/non_blank/  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. Automated Optimization                                      │
│  python tools/optimize_parameters.py --plot                     │
│  → Generates config/optimized_config.json with recommendations  │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. Interactive Fine-Tuning (Optional)                          │
│  python tools/interactive_tuner.py                              │
│  → Visual adjustment with real-time feedback                    │
│  → Saves config/tuned_config.json                               │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  4. Validation & Comparison                                     │
│  python tools/validate_parameters.py --compare-all              │
│  → Compare current vs optimized vs tuned parameters             │
│  → Get accuracy, precision, recall, F1-score                    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
              Update config/config.py with best parameters
```

---

## Tool 1: Sample Extraction Tool

**File**: `extract_samples.py`

### Purpose
Creates a labeled dataset of blank and non-blank pages from your actual medical report PDFs for use in parameter optimization.

### Usage

#### Interactive Mode (Recommended)
```bash
python tools/extract_samples.py --pdf input/medical_reports.pdf --mode interactive
```

**Interactive mode features:**
- Displays each page visually with current detection metrics
- You manually classify each page as blank (b) or non-blank (n)
- Skip pages (s) or quit anytime (q)
- See current detection metrics for each page to understand edge cases

#### Automatic Mode
```bash
python tools/extract_samples.py --pdf input/reports.pdf --mode auto --threshold 0.7
```

**Automatic mode features:**
- Uses lenient thresholds to auto-extract likely blank/non-blank pages
- `--threshold` sets confidence level (0-1) required for extraction
- Faster but may miss edge cases or ambiguous pages

#### View Summary
```bash
python tools/extract_samples.py --summary
```

### Output Structure
```
samples/
├── blank/                      # Labeled blank pages
│   ├── report1_page_0003.png
│   ├── report1_page_0007.png
│   └── ...
├── non_blank/                  # Labeled non-blank pages
│   ├── report1_page_0001.png
│   ├── report1_page_0002.png
│   └── ...
└── metrics.json                # Detailed metrics for all samples
```

### Best Practices
- **Sample diversity**: Extract samples from multiple PDFs to capture variations
- **Balance**: Aim for roughly equal numbers of blank and non-blank samples
- **Edge cases**: Include challenging cases (nearly-blank, low-quality scans, noise)
- **Quantity**: 20-50 samples total is usually sufficient (10+ of each type)

### Tips
- Focus on pages where current detection fails (false negatives/positives)
- Include examples of different scanning qualities and paper types
- You can run the tool multiple times on different PDFs to build up your dataset

---

## Tool 2: Automated Parameter Optimizer

**File**: `optimize_parameters.py`

### Purpose
Analyzes labeled samples using statistical methods to automatically determine optimal detection thresholds.

### Usage

#### Basic Optimization
```bash
python tools/optimize_parameters.py
```

#### With Distribution Plots
```bash
python tools/optimize_parameters.py --plot --plot-output samples/distributions.png
```

#### Custom Output Path
```bash
python tools/optimize_parameters.py --output config/my_optimized_config.json
```

### How It Works

The optimizer uses several statistical techniques:

1. **Distribution Analysis**
   - Calculates min, max, mean, median, and percentiles for each metric
   - Analyzes both blank and non-blank page distributions separately

2. **Threshold Optimization**
   - Tests all possible threshold values
   - For each threshold, calculates:
     - True Positives (TP): Blank pages correctly identified
     - False Positives (FP): Non-blank pages incorrectly marked blank
     - True Negatives (TN): Non-blank pages correctly identified
     - False Negatives (FN): Blank pages missed
   - Selects threshold with highest accuracy and F1-score

3. **Multi-Criteria Evaluation**
   - Optimizes each parameter independently
   - Provides accuracy, precision, recall, and F1-score for each
   - Calculates overall confidence score

### Output

#### 1. Console Report
```
======================================================================
BLANK PAGE DETECTION - PARAMETER OPTIMIZATION REPORT
======================================================================

SAMPLE SUMMARY
----------------------------------------------------------------------
Total samples: 35
  Blank pages: 18
  Non-blank pages: 17

OPTIMIZATION RESULTS
----------------------------------------------------------------------
Overall Confidence: 95.2% (HIGH)

1. VARIANCE THRESHOLD
   Recommended value: 245.50
   Accuracy: 94.3%
   Precision: 94.4%, Recall: 94.4%, F1: 0.944
   Blank pages variance: 12.45 - 234.67 (median: 89.23)
   Non-blank variance: 456.78 - 2345.12 (median: 1234.56)
...
```

#### 2. Configuration File (`config/optimized_config.json`)
```json
{
  "blank_detection": {
    "variance_threshold": 245.5,
    "edge_threshold": 125,
    "white_pixel_ratio": 0.9234,
    "use_edge_detection": true,
    "canny_low": 50,
    "canny_high": 150
  },
  "optimization_metadata": {
    "overall_confidence": 0.952,
    "sample_count": {
      "blank": 18,
      "non_blank": 17
    },
    "parameter_details": { ... }
  }
}
```

#### 3. Distribution Plots (if `--plot` specified)
- Histogram comparisons of variance, white ratio, and edge count
- Box plots showing metric distributions
- Visual separation of blank vs non-blank pages

### Interpreting Results

**Overall Confidence**:
- **HIGH (>90%)**: Excellent separation, parameters are reliable
- **MEDIUM (75-90%)**: Good separation, but consider fine-tuning
- **LOW (<75%)**: Poor separation, may need more/better samples

**What to check**:
- Are blank and non-blank distributions well-separated?
- Do the recommended thresholds fall between the two distributions?
- Is the accuracy/F1-score acceptable for your use case?

---

## Tool 3: Interactive Parameter Tuner

**File**: `interactive_tuner.py`

### Purpose
Provides a visual GUI for fine-tuning parameters with real-time feedback on classification results.

### Usage

```bash
python tools/interactive_tuner.py
```

If optimized config exists, it will be loaded as the starting point. Otherwise, default parameters are used.

### Interface Features

The interactive tuner window shows:

**Left Panel - Image Display**
- Current sample page image
- Sample number (e.g., "Sample 12/35")
- Classification result: ✓ CORRECT or ✗ INCORRECT
- True label vs Predicted label

**Right Panel - Metrics Display**
- **Current Page Metrics**:
  - Variance: actual value vs threshold
  - White Ratio: actual value vs threshold
  - Edge Count: actual value vs threshold
  - Indicators showing which direction makes it blank/non-blank

- **Overall Performance** (across all samples):
  - Accuracy, Precision, Recall, F1-Score
  - Confusion matrix (TP, FP, TN, FN)
  - Correct/Incorrect counts

**Bottom Panel - Controls**
- **Variance Threshold Slider**: Adjust 0-2000
- **Edge Threshold Slider**: Adjust 0-1000
- **White Ratio Slider**: Adjust 0.0-1.0
- **Navigation Buttons**: Previous / Next sample
- **Save Config Button**: Save current parameters to `config/tuned_config.json`

### How to Use

1. **Start the tuner**
   ```bash
   python tools/interactive_tuner.py
   ```

2. **Adjust parameters with sliders**
   - Move sliders and watch classification change in real-time
   - Check overall performance metrics as you adjust
   - Goal: Maximize accuracy/F1-score

3. **Navigate through samples**
   - Use Previous/Next buttons to see different examples
   - Pay special attention to misclassified samples
   - Adjust parameters to fix misclassifications

4. **Iterate and refine**
   - Look for patterns in misclassified samples
   - Try to balance false positives vs false negatives
   - Aim for high overall accuracy while maintaining good recall

5. **Save when satisfied**
   - Click "Save Config" button
   - Configuration saved to `config/tuned_config.json`

### Tips for Tuning

**For false negatives (blank pages not detected):**
- **Increase** variance threshold (allows higher variance blank pages)
- **Increase** edge threshold (allows more edges in blank pages)
- **Decrease** white ratio threshold (allows less white in blank pages)

**For false positives (non-blank pages marked as blank):**
- **Decrease** variance threshold (stricter about variance)
- **Decrease** edge threshold (stricter about edge count)
- **Increase** white ratio threshold (requires more white)

**Finding balance:**
- The system uses 2-out-of-3 voting, so you have flexibility
- If one metric isn't discriminative, adjust the others
- Watch the overall metrics, not just individual pages

---

## Tool 4: Parameter Validation Script

**File**: `validate_parameters.py`

### Purpose
Validates proposed parameters against labeled samples and compares performance of different configurations.

### Usage

#### Validate Optimized Config
```bash
python tools/validate_parameters.py
```

#### Compare All Available Configs
```bash
python tools/validate_parameters.py --compare-all
```

This compares:
- Current (default from `config/config.py`)
- Optimized (from `config/optimized_config.json`)
- Tuned (from `config/tuned_config.json`)

#### Validate Specific Configs
```bash
python tools/validate_parameters.py \
  --config config/optimized_config.json \
  --config config/tuned_config.json
```

#### Custom Plot Output
```bash
python tools/validate_parameters.py --compare-all --plot-output results/validation.png
```

### Output

#### 1. Comparison Summary Table
```
Configuration         Accuracy     Precision    Recall       F1-Score
--------------------------------------------------------------------------------
Current (Default)       77.1%        75.0%        80.0%      0.774
Optimized               94.3%        94.4%        94.4%      0.944
Tuned                   97.1%        96.7%        97.2%      0.970
```

#### 2. Detailed Results for Each Config
```
================================================================================
CONFIGURATION: Optimized
================================================================================

Parameters:
  Variance Threshold:   245.50
  Edge Threshold:       125
  White Pixel Ratio:    0.9234 (92.3%)
  Use Edge Detection:   True

Performance Metrics:
  Accuracy:    94.3%
  Precision:   94.4%
  Recall:      94.4%
  Specificity: 94.1%
  F1-Score:    0.944

Confusion Matrix:
                 Predicted Blank    Predicted Non-Blank
  Actual Blank           17                  1
  Actual Non-Blank        1                 16

Misclassified Samples: 2
  1. report1_page_0003.png
     True: blank, Predicted: non_blank
     Variance: 267.34, White Ratio: 91.2%, Edges: 134
  2. report2_page_0015.png
     True: non_blank, Predicted: blank
     Variance: 123.45, White Ratio: 95.6%, Edges: 45
```

#### 3. Visualization (PNG file)
- Bar chart comparing all metrics across configurations
- F1-Score horizontal bar chart
- Confusion matrices for each configuration
- Saved to `samples/validation_comparison.png` (or custom path)

### Interpreting Results

**Metrics Explained**:
- **Accuracy**: Overall correctness (TP + TN) / Total
- **Precision**: Of pages marked blank, how many actually are? TP / (TP + FP)
- **Recall**: Of actual blank pages, how many did we catch? TP / (TP + FN)
- **Specificity**: Of actual non-blank pages, how many did we correctly identify? TN / (TN + FP)
- **F1-Score**: Harmonic mean of precision and recall (balances both)

**Which metric matters most?**
- **High recall is critical** if you can't afford to miss blank pages (false negatives)
- **High precision is critical** if you can't afford to remove content pages (false positives)
- **F1-score balances both** - generally the best single metric
- **Accuracy** can be misleading if classes are imbalanced

**Making decisions**:
- Compare F1-scores - higher is better
- Check misclassified samples to understand failure modes
- Consider your use case: is a false positive or false negative worse?
- Look for configuration with acceptable trade-offs

---

## Tool 5: Config Runner

**File**: `run_with_config.py`

### Purpose
Easily run the PDF processing pipeline with different configurations without modifying the main config file.

### Usage

#### Run with Optimized Config
```bash
python tools/run_with_config.py --config optimized --input input/report.pdf --output output/
```

#### Run with Tuned Config
```bash
python tools/run_with_config.py --config tuned --input input/report.pdf --output output/
```

#### Run with Current Default Config
```bash
python tools/run_with_config.py --config current --input input/report.pdf --output output/
```

#### Run with Custom Config File
```bash
python tools/run_with_config.py --config my_custom_config.json --input input/report.pdf --output output/
```

### Commands

#### List Available Configurations
```bash
python tools/run_with_config.py --list
```

Output:
```
============================================================
AVAILABLE CONFIGURATIONS
============================================================

✓ current      - Current default configuration from config/config.py
✓ optimized    - Automatically optimized parameters from sample analysis
✗ tuned        - Manually tuned parameters from interactive tuner
              File: config/tuned_config.json (not found)

============================================================
```

#### Show Configuration Details
```bash
python tools/run_with_config.py --info optimized
```

Shows detailed parameter values and metadata for the specified configuration.

#### Compare Configurations
```bash
python tools/run_with_config.py --compare current optimized tuned
```

Output:
```
==========================================================================================
CONFIGURATION COMPARISON
==========================================================================================

Parameter                      current            optimized                tuned
------------------------------------------------------------------------------------------
Variance Threshold               100.0                245.5                250.0
Edge Threshold                      50                  125                  130
White Pixel Ratio              0.95 (95.0%)      0.9234 (92.3%)       0.9150 (91.5%)
Use Edge Detection                 True                 True                 True
Canny Low                            50                   50                   50
Canny High                          150                  150                  150
==========================================================================================
```

### Why Use This Tool?

**Testing without commitment**: Try different configurations on real PDFs without modifying your main config file.

**Side-by-side comparison**: Process the same PDF with different configs to see which performs better.

**Easy switching**: Quickly test optimized vs tuned parameters to choose the best.

### Examples

**Test optimized config on a single PDF:**
```bash
python tools/run_with_config.py \
  --config optimized \
  --input input/test_report.pdf \
  --output output/test_optimized/ \
  --verbose
```

**Compare results by running with different configs:**
```bash
# Run with current config
python tools/run_with_config.py --config current --input input/test.pdf --output output/current/

# Run with optimized config
python tools/run_with_config.py --config optimized --input input/test.pdf --output output/optimized/

# Compare the outputs
```

---

## Tool 6: Config Manager

**File**: `manage_config.py`

### Purpose
Manage, view, backup, and deploy different blank detection configurations. This tool helps you safely switch between configurations and maintain backups.

### Usage

#### List Available Configurations
```bash
python tools/manage_config.py --list
```

Output:
```
============================================================
AVAILABLE CONFIGURATIONS
============================================================

✓ current     - Active configuration in config/config.py
✓ optimized   - Auto-optimized from sample analysis
✗ tuned       - Manually tuned via interactive tool
              File: config/tuned_config.json (not found)
              Run: python tools/interactive_tuner.py

============================================================
```

#### Show Current Active Configuration
```bash
python tools/manage_config.py --show current
```

Shows the currently active parameters in `config/config.py`.

#### Show Other Configurations
```bash
python tools/manage_config.py --show optimized
python tools/manage_config.py --show tuned
```

Shows parameters and metadata from the specified config file.

#### Preview Deployment (Dry Run)
```bash
python tools/manage_config.py --deploy optimized --dry-run
```

Output:
```
============================================================
DEPLOYING: optimized
============================================================

Parameter                 Current Value      →  New Value
----------------------------------------------------------------------
variance_threshold                 100.0  →  245.5
edge_threshold                        50  →  125
white_pixel_ratio     0.9500 (95.0%)   →  0.9234 (92.3%)
use_edge_detection                  True     True
canny_low                             50     50
canny_high                           150     150

[DRY RUN] No changes made. Remove --dry-run to deploy.
```

#### Deploy Configuration
```bash
python tools/manage_config.py --deploy optimized
```

This will:
1. Show current vs new parameters
2. Create a backup of current `config/config.py`
3. Ask for confirmation
4. Update `config/config.py` with new parameters

Output:
```
============================================================
DEPLOYING: optimized
============================================================

Parameter                 Current Value      →  New Value
----------------------------------------------------------------------
variance_threshold                 100.0  →  245.5
edge_threshold                        50  →  125
white_pixel_ratio     0.9500 (95.0%)   →  0.9234 (92.3%)

This will update config/config.py with 3 parameter change(s).
A backup will be created automatically.

Proceed with deployment? [y/N]: y

Backup created: config/backups/config_backup_20250122_143022.py

✓ Configuration deployed successfully!
✓ 3 parameter(s) updated in config/config.py

To revert, restore from backup: config/backups/config_backup_20250122_143022.py
```

#### List Backups
```bash
python tools/manage_config.py --backups
```

Output:
```
============================================================
CONFIGURATION BACKUPS
============================================================

2025-01-22 14:30:22  -  config_backup_20250122_143022.py  (2847 bytes)
2025-01-22 12:15:10  -  config_backup_20250122_121510.py  (2847 bytes)
2025-01-21 09:45:33  -  config_backup_20250121_094533.py  (2847 bytes)

============================================================
```

#### Restore from Backup
```bash
python tools/manage_config.py --restore config_backup_20250122_143022.py
```

This will:
1. Create a backup of the current config (before restoring)
2. Ask for confirmation
3. Restore the specified backup to `config/config.py`

### Deployment Workflow

**Safe deployment process:**

1. **Test first** using `run_with_config.py`:
   ```bash
   python tools/run_with_config.py --config optimized --input test.pdf --output test_output/
   ```

2. **Preview deployment**:
   ```bash
   python tools/manage_config.py --deploy optimized --dry-run
   ```

3. **Deploy if satisfied**:
   ```bash
   python tools/manage_config.py --deploy optimized
   ```

4. **Test in production**:
   ```bash
   python main.py --input input/report.pdf --output output/
   ```

5. **Rollback if needed**:
   ```bash
   python tools/manage_config.py --backups
   python tools/manage_config.py --restore config_backup_20250122_143022.py
   ```

### Safety Features

- **Automatic backups**: Every deployment creates a timestamped backup
- **Confirmation required**: Won't deploy without explicit confirmation
- **Dry-run mode**: Preview changes before deploying
- **Easy rollback**: Restore from any backup with one command
- **No data loss**: Original config is always preserved

### Why Use This Tool?

**Safe deployment**: Automatically creates backups before making changes.

**Easy rollback**: Quickly revert to any previous configuration.

**Clear visibility**: See exactly what will change before deploying.

**Version history**: Keep track of all configuration changes over time.

---

## Complete Example Workflow

### Step 1: Extract Samples
```bash
# Extract samples from your medical reports
python tools/extract_samples.py --pdf input/medical_reports_batch1.pdf --mode interactive

# Add more samples from another PDF
python tools/extract_samples.py --pdf input/medical_reports_batch2.pdf --mode interactive

# Check your sample collection
python tools/extract_samples.py --summary
```

Expected output:
```
============================================================
SAMPLE COLLECTION SUMMARY
============================================================
Total samples: 35
  Blank pages: 18
  Non-blank pages: 17

Sample directory: D:\Projects\med\samples
Metadata file: D:\Projects\med\samples\metrics.json
...
```

### Step 2: Optimize Parameters
```bash
# Run automated optimization with visualization
python tools/optimize_parameters.py --plot
```

Expected output:
```
INFO: Loaded 18 blank and 17 non-blank samples
INFO: Analyzing metric distributions...
INFO: Computing optimal parameters...
INFO: Optimized config saved to: config\optimized_config.json

======================================================================
BLANK PAGE DETECTION - PARAMETER OPTIMIZATION REPORT
======================================================================
...
Overall Confidence: 95.2% (HIGH)
...
```

### Step 3: Validate Optimized Config
```bash
# Compare optimized vs current default
python tools/validate_parameters.py --compare-all
```

Review the results. If optimized config shows significant improvement (e.g., F1-score: 0.944 vs 0.774), proceed to next step.

### Step 4: Fine-Tune (Optional)
```bash
# Open interactive tuner for visual fine-tuning
python tools/interactive_tuner.py
```

Adjust sliders, navigate through samples, and save when satisfied.

### Step 5: Final Validation
```bash
# Compare all three configurations
python tools/validate_parameters.py --compare-all
```

Review final comparison:
```
Configuration         Accuracy     Precision    Recall       F1-Score
--------------------------------------------------------------------------------
Current (Default)       77.1%        75.0%        80.0%      0.774
Optimized               94.3%        94.4%        94.4%      0.944
Tuned                   97.1%        96.7%        97.2%      0.970

RECOMMENDATION: 'Tuned' has the highest F1-score (0.970)
```

### Step 6: Deploy New Parameters
```bash
# Update your main configuration file
# Copy parameters from config/tuned_config.json to config/config.py
```

Edit `config/config.py`:
```python
BLANK_DETECTION_CONFIG = {
    "variance_threshold": 245.5,      # Updated from 100.0
    "edge_threshold": 125,             # Updated from 50
    "white_pixel_ratio": 0.9234,      # Updated from 0.95
    "use_edge_detection": True,
    "canny_low": 50,
    "canny_high": 150,
}
```

### Step 7: Test on Real Data
```bash
# Run your main processing pipeline with new parameters
python main.py --input input/test_reports.pdf --output output/
```

Monitor the results. If performance is good, you're done! If not, collect more samples focusing on failure cases and repeat the process.

---

## Troubleshooting

### "Metrics file not found"
**Problem**: `optimize_parameters.py` or `validate_parameters.py` can't find `samples/metrics.json`

**Solution**: Run `extract_samples.py` first to create labeled samples.

### "No samples found"
**Problem**: Interactive tuner or optimizer finds no samples

**Solution**: Check that `samples/blank/` and `samples/non_blank/` contain `.png` files.

### Low overall confidence (<75%)
**Problem**: Optimizer reports low confidence in results

**Possible causes**:
- Insufficient sample diversity
- Overlapping distributions (blank and non-blank pages look too similar)
- Poor sample labeling

**Solutions**:
1. Add more samples, especially edge cases
2. Review your labels - ensure consistency
3. Consider if blank detection is possible with current approach
4. Try collecting samples from different PDFs/sources

### Parameters don't improve performance
**Problem**: Optimized config performs similar to or worse than default

**Possible causes**:
- Sample set not representative of real data
- Overfitting to small sample set
- Measurement error

**Solutions**:
1. Expand sample set (aim for 30+ samples)
2. Ensure samples come from multiple PDFs
3. Test on a separate validation set not used in optimization
4. Review misclassified samples to understand patterns

### Interactive tuner shows incorrect results
**Problem**: Tuner classifications don't match expected

**Solution**: This is actually good! It's showing you where parameters fail. Use this information to adjust sliders and improve detection.

---

## Best Practices

### Sample Collection
1. **Quality over quantity**: 20-30 well-chosen samples beat 100 random ones
2. **Include edge cases**: Near-blank pages, noisy scans, partial content
3. **Multiple sources**: Sample from different scanners, paper types, report formats
4. **Balanced dataset**: Equal or near-equal blank and non-blank samples
5. **Representative**: Samples should reflect real-world distribution you'll encounter

### Parameter Optimization
1. **Trust the data**: Automated optimizer uses statistical methods - don't override without reason
2. **Understand trade-offs**: Perfect 100% accuracy is unlikely; balance precision vs recall
3. **Validate thoroughly**: Test on new PDFs not used in optimization
4. **Iterate**: If results aren't good enough, add more samples and re-optimize
5. **Document**: Note which PDFs you used for samples for future reference

### Deployment
1. **Start conservative**: Deploy optimized parameters on a subset of files first
2. **Monitor results**: Check processing logs for unexpected behavior
3. **Collect feedback**: Note any false positives/negatives in production
4. **Re-optimize periodically**: As you get new report formats, update samples and re-run

---

## Files Generated

| File | Description | Generated By |
|------|-------------|--------------|
| `samples/blank/*.png` | Labeled blank page images | extract_samples.py |
| `samples/non_blank/*.png` | Labeled non-blank page images | extract_samples.py |
| `samples/metrics.json` | Detailed metrics for all samples | extract_samples.py |
| `config/optimized_config.json` | Automatically optimized parameters | optimize_parameters.py |
| `samples/distributions.png` | Metric distribution plots | optimize_parameters.py (--plot) |
| `config/tuned_config.json` | Manually tuned parameters | interactive_tuner.py |
| `samples/validation_comparison.png` | Validation comparison plots | validate_parameters.py |

---

## Command Reference

### extract_samples.py
```bash
# Interactive labeling
python tools/extract_samples.py --pdf <path> --mode interactive

# Automatic extraction
python tools/extract_samples.py --pdf <path> --mode auto --threshold 0.7

# View summary
python tools/extract_samples.py --summary

# Custom samples directory
python tools/extract_samples.py --pdf <path> --samples-dir custom_samples/
```

### optimize_parameters.py
```bash
# Basic optimization
python tools/optimize_parameters.py

# With distribution plots
python tools/optimize_parameters.py --plot

# Custom paths
python tools/optimize_parameters.py \
  --samples-dir custom_samples/ \
  --output config/my_config.json \
  --plot-output results/plots.png
```

### interactive_tuner.py
```bash
# Run tuner
python tools/interactive_tuner.py

# Custom samples directory
python tools/interactive_tuner.py --samples-dir custom_samples/
```

### validate_parameters.py
```bash
# Validate optimized config
python tools/validate_parameters.py

# Compare all configs
python tools/validate_parameters.py --compare-all

# Compare specific configs
python tools/validate_parameters.py \
  --config config/optimized_config.json \
  --config config/tuned_config.json

# Custom paths
python tools/validate_parameters.py \
  --compare-all \
  --samples-dir custom_samples/ \
  --plot-output results/validation.png
```

### run_with_config.py
```bash
# List available configs
python tools/run_with_config.py --list

# Show config info
python tools/run_with_config.py --info optimized

# Compare configs
python tools/run_with_config.py --compare current optimized tuned

# Run with specific config
python tools/run_with_config.py \
  --config optimized \
  --input input/report.pdf \
  --output output/ \
  --verbose

# Run with custom config file
python tools/run_with_config.py \
  --config my_config.json \
  --input input/report.pdf \
  --output output/
```

### manage_config.py
```bash
# List available configs
python tools/manage_config.py --list

# Show current config
python tools/manage_config.py --show current

# Show other configs
python tools/manage_config.py --show optimized
python tools/manage_config.py --show tuned

# Preview deployment (dry run)
python tools/manage_config.py --deploy optimized --dry-run

# Deploy configuration
python tools/manage_config.py --deploy optimized
python tools/manage_config.py --deploy tuned

# List backups
python tools/manage_config.py --backups

# Restore from backup
python tools/manage_config.py --restore config_backup_20250122_143022.py
```

---

## FAQ

**Q: How many samples do I need?**

A: 20-30 total samples is usually sufficient (10-15 of each type). More is better, but quality and diversity matter more than quantity.

**Q: Do I need to use all six tools?**

A: No. At minimum, use `extract_samples.py` and `optimize_parameters.py` to find optimal parameters. The other tools (`interactive_tuner.py`, `validate_parameters.py`, `run_with_config.py`, `manage_config.py`) are optional but make the process easier and safer.

**Q: Can I add more samples later?**

A: Yes! Just run `extract_samples.py` again. It will append to your existing `metrics.json`.

**Q: What if optimized parameters are worse than default?**

A: Your samples may not be representative. Try collecting more samples from diverse sources, or check your labeling for consistency.

**Q: Should I use interactive or auto mode for extraction?**

A: Interactive mode is recommended for accuracy. Auto mode is faster but may mislabel edge cases.

**Q: How do I know which config to use?**

A: Run `validate_parameters.py --compare-all` and pick the one with the highest F1-score. If they're close, choose based on whether precision or recall matters more to you.

**Q: Can I optimize for specific metrics (e.g., maximize recall)?**

A: The current optimizer maximizes overall accuracy/F1-score. For custom optimization, use the interactive tuner to manually prioritize recall.

**Q: What if I have multiple types of medical reports?**

A: Collect samples from each type. If they're very different, consider creating separate configs for each type.

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the console output for error messages
3. Verify your samples directory structure is correct
4. Ensure you've run the tools in the correct order

---

*Happy optimizing! May your blank pages be accurately detected.*
