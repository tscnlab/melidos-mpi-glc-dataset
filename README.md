# MeLiDos MPI GLC dataset

This repository contains the Max Planck Institute for Biological Cybernetics
(MPI KYB) site data from the MeLiDos field study, refactored as a Global Light
Commons (GLC) Schema 3.0.2 Data Package.

The source dataset is the [Personal light exposure dataset for Tuebingen,
Germany](https://github.com/MeLiDosProject/GuidolinEtAl_Dataset_2025), archived
at [Zenodo](https://doi.org/10.5281/zenodo.16895188). The GLC refactor preserves
the source measurements and adds machine-readable study, participant, device,
file, variable, and preprocessing metadata.

## MPI-specific processing

- The published participant set contains 26 retained IDs. The source study-date
  workbook instead uses 26 sequential enrolment IDs. The refactoring scripts
  apply an explicit row-by-row mapping verified against the ActLumus serial
  numbers; they do not rely on positional participant matching at package use
  time.
- Near-corneal ActLumus records use the source repository's imported,
  trial-filtered data and documented gap handling.
- ActTrust2 wrist records were present only as raw logs. They were decoded,
  restricted to the corrected participant trial intervals, and included
  without resampling, aggregation, or synthetic gap rows.
- Weekly rooftop ActLumus logs were also present only in raw form. They were
  concatenated chronologically and are represented as a separate,
  non-participant-associated environmental dataset.
- The source metadata reports that devices were not calibrated and supplies no
  calibration records. Because GLC 3.0.2 requires a calibration date, each
  device uses its earliest documented deployment date as a clearly identified
  provisional proxy. These dates are not evidence that calibration occurred.
- The lifestyle and health questionnaire is absent from the source dataset and
  is therefore not represented in this package.

Only participant near-corneal ActLumus files are marked `primary`, and only
`MEDI` is marked as their primary variable. ActTrust wrist, rooftop ambient,
questionnaire, diary, wear-log, and study-timing files are supporting data.

## Contents

- `datapackage.json`: package descriptor
- `data/`: GLC metadata and participant, sensor, questionnaire, diary, timing,
  and environmental CSV files
- `schemas/3.0.2/`: schemas used for validation
- `glc_validation/`: reproducible refactoring scripts and reviewed variable
  metadata
- `.github/workflows/validate-glc-dataset.yml`: automated GLC validation

The measurement and questionnaire content should be interpreted together with
the documentation and limitations in the original source repository.
