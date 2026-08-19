#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) {
  stop("Usage: split_imported_by_participant.R SOURCE_ROOT OUTPUT_ROOT")
}

if (!grepl("UTF-8", Sys.getlocale("LC_CTYPE"), fixed = TRUE)) {
  locale <- Sys.setlocale("LC_CTYPE", "en_US.UTF-8")
  if (!grepl("UTF-8", locale, fixed = TRUE)) stop("A UTF-8 locale is required")
}

source_root <- normalizePath(args[[1]], mustWork = TRUE)
output_root <- args[[2]]
imported_root <- file.path(source_root, "data", "imported")

# The study-date workbook retained the original sequential enrolment IDs,
# whereas the published repository uses the final IDs after withdrawals.
# Row order and ActLumus serial numbers establish this complete mapping.
final_ids <- sprintf("MPI_S%03d", c(
  201, 202, 204, 205, 206, 208, 209, 210, 212, 213, 214, 215, 216,
  218, 219, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231
))
workbook_ids <- sprintf("MPI_S%03d", 201:226)
trial_id_map <- setNames(final_ids, workbook_ids)

files <- list.files(
  imported_root,
  pattern = "\\.[Rr][Dd]ata$",
  recursive = TRUE,
  full.names = TRUE
)
excluded <- grepl("[/\\\\]light[/\\\\].*_1minute\\.[Rr][Dd]ata$", files)
eligible <- sort(files[!excluded])

if (!length(eligible)) stop("No eligible RData files found")

dir.create(output_root, recursive = TRUE, showWarnings = FALSE)
manifest <- list()
manifest_i <- 0L

csv_value <- function(x) {
  if (inherits(x, "POSIXt")) {
    timezone <- attr(x, "tzone")
    timezone <- if (is.null(timezone) || !length(timezone) || is.na(timezone[[1L]])) "" else timezone[[1L]]
    return(format(x, "%Y-%m-%d %H:%M:%S", tz = timezone))
  }
  if (inherits(x, "Date")) return(format(x, "%Y-%m-%d"))
  # Preserve an R factor's stored ordering in the CSV. The corresponding
  # metadata pairs these one-based positions with levels(x), allowing the
  # original factor to be reconstructed after a CSV round trip.
  if (is.factor(x)) return(as.integer(x))
  x
}

for (path in eligible) {
  env <- new.env(parent = emptyenv())
  objects <- load(path, envir = env)
  tabular <- objects[vapply(objects, function(nm) is.data.frame(env[[nm]]), logical(1))]
  if (length(tabular) != 1L) {
    stop(sprintf("Expected exactly one tabular object in %s; found: %s", path, paste(tabular, collapse = ", ")))
  }

  object_name <- tabular[[1L]]
  dat <- env[[object_name]]
  if (!"Id" %in% names(dat)) stop(sprintf("Missing Id column in %s", path))
  if (basename(path) == "trial_times.RData") {
    original_ids <- as.character(dat$Id)
    if (any(!original_ids %in% names(trial_id_map))) stop("Unexpected ID in trial_times.RData")
    dat$Id <- unname(trial_id_map[original_ids])
  }
  if (anyNA(dat$Id) || any(!nzchar(as.character(dat$Id)))) stop(sprintf("Blank participant Id in %s", path))
  invalid_id <- !as.character(dat$Id) %in% final_ids
  if (any(invalid_id)) {
    message(sprintf(
      "%s: excluding %d row(s) with non-participant IDs: %s",
      relative <- substring(path, nchar(imported_root) + 2L),
      sum(invalid_id),
      paste(sort(unique(as.character(dat$Id[invalid_id]))), collapse = ", ")
    ))
    dat <- dat[!invalid_id, , drop = FALSE]
  }

  relative <- substring(path, nchar(imported_root) + 2L)
  relative_dir <- dirname(relative)
  stem <- sub("\\.[Rr][Dd]ata$", "", basename(relative))
  destination_dir <- file.path(output_root, "data", "imported", relative_dir)
  dir.create(destination_dir, recursive = TRUE, showWarnings = FALSE)

  ids <- sort(unique(as.character(dat$Id)))
  written_rows <- 0L
  for (id in ids) {
    participant <- dat[as.character(dat$Id) == id, , drop = FALSE]
    participant_parts <- list(participant)
    output_stems <- stem

    for (part_i in seq_along(participant_parts)) {
      participant_part <- participant_parts[[part_i]]
      participant_part[] <- lapply(participant_part, csv_value)
      output_name <- paste0(id, "_", output_stems[[part_i]], ".csv")
      output_path <- file.path(destination_dir, output_name)
      write.csv(participant_part, output_path, row.names = FALSE, na = "", fileEncoding = "UTF-8")
      written_rows <- written_rows + nrow(participant_part)

      manifest_i <- manifest_i + 1L
      manifest[[manifest_i]] <- data.frame(
        source_file = file.path("data", "imported", relative),
        source_object = object_name,
        participant_id = id,
        output_file = file.path("data", "imported", relative_dir, output_name),
        rows = nrow(participant_part),
        columns = ncol(participant_part),
        stringsAsFactors = FALSE
      )
    }
  }
  if (written_rows != nrow(dat)) stop(sprintf("Row-count mismatch for %s", path))
  message(sprintf("%s: %d rows -> %d participant files", relative, nrow(dat), length(ids)))
  rm(dat, env)
  invisible(gc())
}

manifest_df <- do.call(rbind, manifest)
write.csv(manifest_df, file.path(output_root, "split_manifest.csv"), row.names = FALSE, na = "", fileEncoding = "UTF-8")

excluded_relative <- substring(files[excluded], nchar(source_root) + 2L)
writeLines(sort(excluded_relative), file.path(output_root, "excluded_files.txt"), useBytes = TRUE)
message(sprintf("Complete: %d source files -> %d participant CSV files", length(eligible), nrow(manifest_df)))
