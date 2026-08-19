# MPI refactoring scripts

These scripts were adapted from the MeLiDos IZTECH and KNUST GLC refactoring workflows.
They extract the source metadata workbook, split imported RData tables by
participant, generate and apply variable metadata, build the GLC package,
recover questionnaire timestamps where available, enforce unit rules, omit
empty optional JSON properties, and prepare the publishable directory layout.

The participant-prefix handling in `apply_variable_dictionary.py` and
`update_questionnaire_datetimes.py` is site-independent so it can be reused
for later MeLiDos sites. `build_glc_package.py` contains the MPI-specific
study mapping, preprocessing provenance, and participant selection.

The source RData files were split one at a time because loading every
multi-million-row light table in one R process exceeded the available memory.
