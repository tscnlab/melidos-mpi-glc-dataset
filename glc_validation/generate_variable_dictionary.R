#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
output <- if (length(args)) args[[1L]] else "glc_validation/variable_dictionary.csv"

files <- list.files(
  "data/imported",
  pattern = "\\.[Rr][Dd]ata$",
  recursive = TRUE,
  full.names = TRUE
)
files <- files[!grepl("[/\\\\]light[/\\\\].*_1minute\\.[Rr][Dd]ata$", files)]

type_from_class <- function(x) {
  if (is.factor(x)) return("factor")
  if (is.logical(x)) return("boolean")
  if (is.integer(x)) return("integer")
  if (is.numeric(x) || inherits(x, "difftime")) return("numeric")
  "string"
}

proposed_type <- function(source, name, x) {
  if (source == "exercisediary" && name == "light_glasses") return("boolean")
  if (source == "wearlog" && name %in% c("wearlog_bp", "wearlog_bag", "wearlog_motion"))
    return("boolean")
  if (
    source %in% c("light_chest", "light_glasses", "light_wrist") &&
    name == "EVENT"
  ) return("integer")
  if (
    source %in% c("light_chest", "light_glasses", "light_wrist") &&
    name %in% c("ORIENTATION", "STATE")
  ) return("factor")
  if (source == "sleepdiaries" && name == "awakenings") return("integer")
  type_from_class(x)
}

factor_levels <- function(x, proposed_type) {
  if (is.factor(x)) return(paste(levels(x), collapse = " | "))
  if (proposed_type != "factor") return("")
  values <- sort(unique(x[!is.na(x)]))
  paste(as.character(values), collapse = " | ")
}

reviewer_note <- function(source, name) {
  if (source == "exercisediary" && name == "light_glasses")
    return("Boolean-coded in the source as 0 = no and 1 = yes; empty values represent missing responses.")
  if (source == "wearlog" && name %in% c("wearlog_bp", "wearlog_bag", "wearlog_motion"))
    return("Boolean-coded in the source as 0 = no and 1 = yes; empty values represent missing responses.")
  if (
    source %in% c("light_chest", "light_glasses", "light_wrist") &&
    name == "EVENT"
  ) return("Integer event-marker code exported by the ActLumus device; code meanings require ActLumus documentation.")
  if (
    source %in% c("light_chest", "light_glasses", "light_wrist") &&
    name %in% c("ORIENTATION", "STATE")
  ) return("Numeric device codes proposed as factors; code meanings and labels require ActLumus documentation.")
  if (
    source %in% c("light_chest", "light_glasses", "light_wrist") &&
    name %in% c("CAP_SENS_1", "CAP_SENS_2")
  ) return("Arbitrary units assigned provisionally; confirm the ActLumus capacitive-channel scale with Condor or the data provider.")
  if (
    source %in% c("light_chest", "light_glasses", "light_wrist") &&
    name %in% c("PIM", "PIMn", "TAT", "TATn", "ZCM", "ZCMn")
  ) return("Activity-unit terminology is provisional and requires confirmation from ActLumus documentation or the data provider.")
  if (
    source %in% c("light_chest", "light_glasses", "light_wrist") &&
    name %in% c("AMB.LIGHT", "RED.LIGHT", "GREEN.LIGHT", "BLUE.LIGHT", "UVA.LIGHT", "UVB.LIGHT")
  ) return("Condor export specification unit applied. This field contains only zero or missing values in the MeLiDos imported data and should not be interpreted as an observed signal.")
  ""
}

humanize <- function(name) {
  exceptions <- c(
    "Id" = "Participant ID",
    "Datetime" = "Date and time",
    "file.name" = "Source recording file name",
    "is.implicit" = "Implicitly generated timestamp indicator",
    "MEDI" = "Melanopic equivalent daylight illuminance",
    "LIGHT" = "Photopic illuminance",
    "TEMPERATURE" = "Temperature",
    "EXT.TEMPERATURE" = "External temperature",
    "AMB.LIGHT" = "Ambient light",
    "IR.LIGHT" = "Infrared light",
    "CAP_SENS_1" = "Wrist-contact sensor 1",
    "CAP_SENS_2" = "Wrist-contact sensor 2",
    "RED.LIGHT" = "Red light channel",
    "GREEN.LIGHT" = "Green light channel",
    "BLUE.LIGHT" = "Blue light channel",
    "UVA.LIGHT" = "UVA light channel",
    "UVB.LIGHT" = "UVB light channel",
    "ORIENTATION" = "Device orientation",
    "position" = "Device wearing position"
  )
  if (name %in% names(exceptions)) return(unname(exceptions[[name]]))
  label <- gsub("[._]+", " ", name)
  label <- gsub("([a-z])([A-Z])", "\\1 \\2", label)
  paste0(toupper(substr(label, 1L, 1L)), substr(label, 2L, nchar(label)))
}

is_prompt_like <- function(label) {
  if (!nzchar(label)) return(FALSE)
  grepl("?", label, fixed = TRUE) ||
    grepl("\n", label, fixed = TRUE) ||
    nchar(label) > 45L ||
    grepl(
      "^(How|What|When|Where|Which|Who|Why|Please|Select|Are|Did|Do|Does|Has|Is|I |My |Wearing|There |Can |In what|At the|This experiment)",
      label,
      ignore.case = TRUE
    )
}

concise_labels <- c(
  "acceptability::affective_attitude" = "Comfort while wearing light glasses",
  "acceptability::burden" = "Effort of wearing light glasses",
  "acceptability::ethicality" = "Perceived ethical consequences",
  "acceptability::perceived_effectiveness" = "Perceived measurement effectiveness",
  "acceptability::intervention_coherence" = "Understanding of measurement purpose",
  "acceptability::self_efficacy" = "Confidence while wearing light glasses",
  "acceptability::opportunity_costs" = "Interference with other priorities",
  "acceptability::general_acceptability" = "Overall light-glasses acceptability",
  "ase::slypos_ase_001" = "Excessive light",
  "ase::slypos_ase_002" = "Insufficient light",
  "ase::slypos_ase_003" = "Excessive noise",
  "ase::slypos_ase_004" = "Excessive quiet",
  "ase::slypos_ase_005" = "Excessive warmth",
  "ase::slypos_ase_006" = "Excessive coolness",
  "ase::slypos_ase_007" = "Excessive humidity",
  "ase::slypos_ase_008" = "Uncomfortable smell",
  "ase::slypos_ase_009" = "Uncomfortable bedding",
  "ase::slypos_ase_010" = "Sleeping surface too firm",
  "ase::slypos_ase_011" = "Sleeping surface too soft",
  "ase::slypos_ase_012" = "Other sleeping-surface discomfort",
  "ase::slypos_ase_0123" = "Feeling unsafe or insecure",
  "currentconditions::currentlight" = "Main light source",
  "currentconditions::check_mixedlight" = "Additional light exposure",
  "currentconditions::additional_light" = "Additional light source",
  "currentconditions::kss" = "Recent sleepiness",
  "exercisediary::instructions" = "Exercise-diary confirmation",
  "exercisediary::intensity" = "Physical-activity intensity",
  "exercisediary::location" = "Physical-activity location",
  "exercisediary::type" = "Physical-activity type",
  "exercisediary::commute" = "Active commuting duration",
  "exercisediary::sedentary" = "Sedentary duration",
  "exercisediary::light_glasses" = "Light glasses worn during exercise",
  "experiencelog::exp_time" = "Experience time",
  "experiencelog::type" = "Experience type",
  "experiencelog::location" = "Experience location",
  "experiencelog::loc_spec" = "Location specification",
  "experiencelog::descr" = "Experience description",
  "experiencelog::feedback" = "Feedback from others",
  "experiencelog::identity" = "Feedback provider",
  "experiencelog::identity_spec" = "Feedback-provider specification",
  "experiencelog::social_type" = "Feedback type",
  "experiencelog::removal" = "Light-glasses removal prompted",
  "experiencelog::future_use" = "Effect on future light-glasses use",
  "lightexposurediary::mhlea_confidence" = "Light-exposure classification confidence",
  "lightexposurediary::activity_desc" = "Activity description",
  "lightexposurediary::activity_desc_english" = "Activity description (English translation)",
  "sleepdiaries::bedtime" = "Bedtime",
  "sleepdiaries::sleepprep" = "Attempted sleep time",
  "sleepdiaries::wake" = "Final awakening time",
  "sleepdiaries::out_ofbed" = "Out-of-bed time",
  "sleepdiaries::sleepdelay" = "Sleep-onset latency",
  "sleepdiaries::awakenings" = "Number of awakenings",
  "sleepdiaries::awake_duration" = "Total awakening duration",
  "sleepdiaries::sleepquality" = "Subjective sleep quality",
  "sleepdiaries::daytype2" = "Day type",
  "sleepdiaries::comments" = "Sleep-diary comments",
  "wearlog::reason" = "Removal reason",
  "wearlog::radius" = "General location",
  "wearlog::wearlog_bp" = "Light-glasses button pressed",
  "wearlog::wearlog_bag" = "Light glasses stored in provided bag",
  "wearlog::wearlog_place" = "Light-glasses placement",
  "wearlog::wearlog_motion" = "Light glasses in motion",
  "wellbeingdiary::who5_1998_1" = "Cheerfulness and good spirits",
  "wellbeingdiary::who5_1998_2" = "Calmness and relaxation",
  "wellbeingdiary::who5_1998_3" = "Activity and vigour",
  "wellbeingdiary::who5_1998_4" = "Previous-night sleep quality",
  "wellbeingdiary::who5_1998_5" = "Interest in daily life",
  "demographics::native_language" = "Questionnaire language is native language",
  "demographics::language_specification" = "Questionnaire-language proficiency",
  "demographics::comments" = "Additional demographic comments",
  "evaluation::glasses_use" = "Usual glasses use",
  "evaluation::general_feeling" = "Overall light-glasses experience",
  "evaluation::challenges" = "Light-glasses challenges and coping",
  "evaluation::act_impact" = "Daily-activity impact",
  "evaluation::beh_adapt" = "Behavioural adaptations",
  "evaluation::social" = "Social reactions",
  "evaluation::improvements" = "Suggested design improvements",
  "evaluation::change_behavior" = "Questionnaire-related behaviour change",
  "health::medication" = "Current medication use",
  "health::medication_type" = "Medication specification",
  "health::tobacco" = "Regular tobacco use",
  "health::drugs" = "Regular recreational-drug use",
  "health::disorder" = "Diagnosed sleep or psychiatric disorder",
  "health::gen_health" = "General health",
  "health::visual_acuity" = "Visual-acuity category",
  "vlsq8::sensitivity" = "Daylight visual sensitivity frequency",
  "vlsq8::glare" = "Ocular glare frequency",
  "vlsq8::flicker" = "Flicker or bright-colour sensitivity frequency",
  "vlsq8::sensitivity_severity" = "Worst visual-sensitivity severity",
  "vlsq8::headache" = "Headache with light sensitivity",
  "vlsq8::blurry_vision" = "Blurred vision with light sensitivity",
  "vlsq8::ability" = "Activity limitation from light sensitivity",
  "vlsq8::glasses" = "Dark-glasses use frequency",
  "leba::leba_f2_04" = "Outdoor time: 30 minutes or less",
  "leba::leba_f2_05" = "Outdoor time: 30-60 minutes",
  "leba::leba_f2_06" = "Outdoor time: 1-3 hours",
  "leba::leba_f2_07" = "Outdoor time: more than 3 hours",
  "leba::leba_f2_08" = "Maximising outdoor time",
  "leba::leba_f2_09" = "Outdoor activity within 2 hours of waking",
  "leba::leba_f3_10" = "Phone use before sleep",
  "leba::leba_f3_11" = "Phone use immediately after waking",
  "leba::leba_f3_12" = "Phone checking during nocturnal awakening",
  "leba::leba_f3_13" = "Smartwatch use before sleep",
  "leba::leba_f3_14" = "Smartwatch checking during nocturnal awakening",
  "leba::leba_f4_15" = "Phone-screen dimming before sleep",
  "leba::leba_f4_16" = "Blue-light filter use before sleep",
  "leba::leba_f4_17" = "Minimal light during nocturnal awakening",
  "leba::leba_f4_18" = "Computer-screen dimming before sleep",
  "leba::leba_f5_19" = "Tunable-light use",
  "leba::leba_f5_20" = "LED use for healthy lighting",
  "leba::leba_f5_21" = "Desk-lamp use for focused work",
  "leba::leba_f5_22" = "Dawn-simulation alarm use",
  "leba::leba_f5_23" = "Immediate light use after waking"
)

concise_label <- function(source, name, embedded_label) {
  if (name == "Id") return("Participant ID")
  key <- paste(source, name, sep = "::")
  if (key %in% names(concise_labels)) return(unname(concise_labels[[key]]))
  if (grepl("_english$", name)) {
    base <- sub("_english$", "", name)
    base_key <- paste(source, base, sep = "::")
    base_label <- if (base_key %in% names(concise_labels))
      unname(concise_labels[[base_key]])
    else
      humanize(base)
    return(paste0(base_label, " (English translation)"))
  }
  if (nzchar(embedded_label) && !is_prompt_like(embedded_label)) return(embedded_label)
  humanize(name)
}

known_units <- c(
  "MEDI" = "lx",
  "LIGHT" = "lx",
  "TEMPERATURE" = "Cel",
  "EXT.TEMPERATURE" = "Cel",
  "MS" = "ms",
  "F1" = "{normalized_sensor_count}",
  "F2" = "{normalized_sensor_count}",
  "F3" = "{normalized_sensor_count}",
  "F4" = "{normalized_sensor_count}",
  "F5" = "{normalized_sensor_count}",
  "F6" = "{normalized_sensor_count}",
  "F7" = "{normalized_sensor_count}",
  "F8" = "{normalized_sensor_count}",
  "CLEAR" = "{normalized_sensor_count}",
  "IR.LIGHT" = "{normalized_sensor_count}",
  "CAP_SENS_1" = "a.u.",
  "CAP_SENS_2" = "a.u.",
  "PIM" = "{activity_count}",
  "PIMn" = "{activity_count}/s",
  "TAT" = "{threshold_count}",
  "TATn" = "{threshold_count}/s",
  "ZCM" = "{crossing_count}",
  "ZCMn" = "{crossing_count}/s",
  "AMB.LIGHT" = "uW/m2",
  "RED.LIGHT" = "uW/cm2",
  "GREEN.LIGHT" = "uW/cm2",
  "BLUE.LIGHT" = "uW/cm2",
  "UVA.LIGHT" = "uW/cm2",
  "UVB.LIGHT" = "uW/cm2"
)

actlumus_supported_units <- c(
  "F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "CLEAR", "IR.LIGHT",
  "AMB.LIGHT", "RED.LIGHT", "GREEN.LIGHT", "BLUE.LIGHT", "UVA.LIGHT", "UVB.LIGHT"
)

actlumus_provisional_units <- c(
  "CAP_SENS_1", "CAP_SENS_2",
  "PIM", "PIMn", "TAT", "TATn", "ZCM", "ZCMn"
)

normalize_unit <- function(unit) {
  normalized <- c(
    "secs" = "s", "sec" = "s", "seconds" = "s", "second" = "s",
    "mins" = "min", "minutes" = "min", "minute" = "min",
    "hours" = "h", "hour" = "h",
    "days" = "d", "day" = "d",
    "years" = "a", "year" = "a",
    "lux" = "lx",
    "degree Celsius" = "Cel"
  )
  if (unit %in% names(normalized)) unname(normalized[[unit]]) else unit
}

known_source_units <- function(source, name) {
  if (
    source %in% c("light_chest", "light_glasses", "light_wrist") &&
    name == "EVENT"
  ) return("{event_code}")
  score_variables <- list(
    ase = "ASE",
    chronotype = "meq",
    wellbeingdiary = "who5_raw",
    leba = c("leba_f2", "leba_f3", "leba_f4", "leba_f5"),
    vlsq8 = "VLSQ8"
  )
  if (source %in% names(score_variables) && name %in% score_variables[[source]])
    return("{score}")
  if (source == "wellbeingdiary" && name == "who5_percentage") return("%")
  if (source == "sleepdiaries" && name == "awakenings") return("{count}")
  if (source == "demographics" && name == "age") return("a")
  ""
}

semantic_term <- function(source, name) {
  # Cross-table identifiers and provenance
  if (name == "Id") return("participant_id")
  if (name == "Datetime") return("datetime")
  if (name == "Date") return("date")
  if (name == "file.name") return("source_file")
  if (name == "is.implicit") return("implicit_record_indicator")
  if (name == "position") return("device_position")

  # ActLumus sensor variables
  if (source %in% c("light_chest", "light_glasses", "light_wrist")) {
    sensor_terms <- c(
      "EVENT" = "device_event",
      "TEMPERATURE" = "temperature",
      "EXT.TEMPERATURE" = "temperature",
      "ORIENTATION" = "device_orientation",
      "PIM" = "activity_metric", "PIMn" = "activity_metric",
      "TAT" = "activity_metric", "TATn" = "activity_metric",
      "ZCM" = "activity_metric", "ZCMn" = "activity_metric",
      "LIGHT" = "photopic_illuminance",
      "MEDI" = "melanopic_edi",
      "IR.LIGHT" = "infrared_light",
      "RED.LIGHT" = "red_light",
      "GREEN.LIGHT" = "green_light",
      "BLUE.LIGHT" = "blue_light",
      "UVA.LIGHT" = "uva_light",
      "UVB.LIGHT" = "uvb_light",
      "CAP_SENS_1" = "capacitive_sensor",
      "CAP_SENS_2" = "capacitive_sensor",
      "CLEAR" = "spectral_channel",
      "STATE" = "device_state",
      "MS" = "device_state",
      "AMB.LIGHT" = "photopic_illuminance"
    )
    if (name %in% names(sensor_terms)) return(unname(sensor_terms[[name]]))
    if (grepl("^F[1-8]$", name)) return("spectral_channel")
    return("other")
  }

  # Derived chronotype and sleep phenotype measures
  if (source == "chronotype") {
    terms <- c(
      "meq_type" = "chronotype_category", "meq" = "meq_score",
      "msf_sc" = "sleep_midpoint", "sjl" = "social_jetlag",
      "so_w" = "sleep_onset", "so_f" = "sleep_onset",
      "sd_w" = "sleep_duration", "sd_f" = "sleep_duration",
      "msw" = "sleep_midpoint", "msf" = "sleep_midpoint",
      "sd_week" = "sleep_duration", "outdoor" = "time_outdoors"
    )
    return(unname(terms[[name]]))
  }

  if (source == "sleepdiaries") {
    terms <- c(
      "bedtime" = "bedtime", "sleepprep" = "bedtime",
      "wake" = "wake_time", "out_ofbed" = "wake_time",
      "sleepdelay" = "sleep_onset", "awakenings" = "sleep_quality",
      "awake_duration" = "sleep_duration", "sleepquality" = "sleep_quality",
      "daytype2" = "sleep_environment", "comments" = "free_text_response",
      "sleep" = "sleep_onset", "sleep_duration" = "sleep_duration",
      "comments_english" = "translated_free_text"
    )
    return(unname(terms[[name]]))
  }

  # Named questionnaire constructs and participant characteristics
  named_terms <- c(
    "ASE" = "ase_score", "VLSQ8" = "vlsq8_score",
    "age" = "age", "sex" = "sex", "gender" = "gender",
    "native_language" = "native_language",
    "language_specification" = "native_language",
    "employment_status" = "employment_status",
    "medication" = "medication_use", "medication_type" = "medication_use",
    "tobacco" = "tobacco_use", "drugs" = "recreational_drug_use",
    "disorder" = "diagnosed_disorder", "gen_health" = "general_health",
    "visual_acuity" = "visual_acuity", "glasses_use" = "visual_acuity"
  )
  if (name %in% names(named_terms)) return(unname(named_terms[[name]]))

  if (source == "acceptability") return("acceptability")
  if (source == "ase") return("questionnaire_item_response")
  if (source == "leba") {
    if (grepl("^leba_f[2-5]$", name)) return("leba_score")
    return("questionnaire_item_response")
  }
  if (source == "vlsq8") {
    if (name %in% c("sensitivity", "sensitivity_severity", "glare", "flicker"))
      return("visual_light_sensitivity")
    return("questionnaire_item_response")
  }
  if (source == "wellbeingdiary") {
    if (name %in% c("who5_raw", "who5_percentage")) return("wellbeing_score")
    if (grepl("^who5_1998_", name)) return("questionnaire_item_response")
  }
  if (source == "evaluation") {
    if (grepl("_english$", name)) return("translated_free_text")
    return("free_text_response")
  }
  if (source == "demographics") return("free_text_response")
  if (source == "health") return("free_text_response")

  # Diaries, experience sampling, and wear logs
  if (source == "currentconditions") {
    if (name %in% c("currentlight", "check_mixedlight", "additional_light"))
      return("light_source_context")
    if (name == "kss") return("sleep_quality")
    if (name == "enddate_4") return("datetime")
    return("wellbeing_score")
  }
  if (source == "exercisediary") {
    if (name %in% c("startdate_3", "enddate_3")) return("datetime")
    if (name == "sedentary") return("sedentary_duration")
    if (name == "location") return("location_context")
    if (name == "light_glasses") return("wear_state")
    if (name %in% c("instructions", "type_english")) return("free_text_response")
    return("exercise_duration")
  }
  if (source == "experiencelog") {
    if (name %in% c("exp_time")) return("datetime")
    if (name %in% c("location", "loc_spec", "loc_spec_english"))
      return("location_context")
    if (name == "removal") return("nonwear_reason")
    if (grepl("_english$", name)) return("translated_free_text")
    return("experience_report")
  }
  if (source == "lightexposurediary") {
    if (name %in% c("start", "end", "startdate")) return("datetime")
    if (grepl("^light", name)) return("light_source_context")
    if (grepl("^act_", name) || name %in% c("activity_desc", "activity_desc_english"))
      return("activity_context")
    if (name == "mhlea_confidence") return("questionnaire_item_response")
  }
  if (source == "wearlog") {
    if (name %in% c("start", "end")) return("datetime")
    if (name == "state") return("wear_state")
    if (name == "reason") return("nonwear_reason")
    if (name %in% c("wearlog_place", "wearlog_place_english"))
      return("device_placement")
    return("wear_state")
  }
  if (source == "wellbeingdiary" && name == "startdate_2") return("datetime")

  if (source == "trial_times") {
    if (name %in% c("start", "end")) return("datetime")
    return("other")
  }

  "other"
}

rows <- list()
for (path in sort(files)) {
  env <- new.env(parent = emptyenv())
  objects <- load(path, envir = env)
  tabular <- objects[vapply(objects, function(name) is.data.frame(env[[name]]), logical(1))]
  if (length(tabular) != 1L) {
    stop(sprintf("Expected one data frame in %s; found %d", path, length(tabular)))
  }

  data <- env[[tabular[[1L]]]]
  source <- sub("\\.[Rr][Dd]ata$", "", basename(path))
  source_relative_path <- substring(path, nchar("data/imported/") + 1L)

  for (name in names(data)) {
    column <- data[[name]]
    embedded_label <- attr(column, "label")
    embedded_label <- if (is.null(embedded_label)) "" else as.character(embedded_label[[1L]])
    proposed_label <- concise_label(source, name, embedded_label)
    proposed_description <- if (is_prompt_like(embedded_label)) embedded_label else ""
    embedded_unit <- attr(column, "units")
    embedded_unit <- if (is.null(embedded_unit)) "" else as.character(embedded_unit[[1L]])
    proposed_unit <- normalize_unit(embedded_unit)
    unit_source <- if (nzchar(embedded_unit)) {
      if (identical(proposed_unit, embedded_unit))
        "embedded R attribute"
      else
        "embedded R attribute; normalized to UCUM"
    } else ""
    if (!nzchar(proposed_unit) && name %in% names(known_units)) {
      proposed_unit <- unname(known_units[[name]])
      unit_source <- if (name == "MEDI") {
        "MeLiDos preprint; normalized to UCUM"
      } else if (name %in% actlumus_supported_units) {
        if (name %in% c("AMB.LIGHT", "RED.LIGHT", "GREEN.LIGHT", "BLUE.LIGHT", "UVA.LIGHT", "UVB.LIGHT"))
          "Condor ActStudio export specification; normalized to UCUM"
        else
          "LightLogR ActLumus spectral documentation"
      } else if (name %in% actlumus_provisional_units) {
        "provisional assignment; confirmation required"
      } else {
        "proposed UCUM unit; verify"
      }
    }
    if (
      !nzchar(proposed_unit) &&
      source == "sleepdiaries" &&
      name %in% c("sleepdelay", "awake_duration")
    ) {
      proposed_unit <- "min"
      unit_source <- "embedded field label; normalized to UCUM"
    }
    variable_type <- proposed_type(source, name, column)
    source_unit <- known_source_units(source, name)
    if (!nzchar(proposed_unit) && nzchar(source_unit)) {
      proposed_unit <- source_unit
      unit_source <- "variable definition; UCUM-style code"
    }
    if (!variable_type %in% c("numeric", "integer")) {
      proposed_unit <- ""
      unit_source <- ""
    }
    unit_review_status <- if (!variable_type %in% c("numeric", "integer")) {
      paste0("not applicable - ", variable_type)
    } else if (name %in% actlumus_provisional_units && nzchar(proposed_unit)) {
      "provisional - confirmation required"
    } else if (nzchar(proposed_unit)) {
      "defined"
    } else {
      "needs definition"
    }

    rows[[length(rows) + 1L]] <- data.frame(
      source_file = source_relative_path,
      source_table = source,
      variable_name = name,
      embedded_label = embedded_label,
      proposed_label = proposed_label,
      label_source = if (!nzchar(embedded_label)) {
        "generated proposal; review"
      } else if (identical(proposed_label, embedded_label)) {
        "embedded R attribute"
      } else {
        "synthesized concise label; review"
      },
      proposed_description = proposed_description,
      description_source = if (nzchar(proposed_description)) "embedded R attribute" else "",
      r_class = paste(class(column), collapse = "/"),
      proposed_type = variable_type,
      embedded_unit = embedded_unit,
      proposed_unit = proposed_unit,
      unit_source = unit_source,
      unit_review_status = unit_review_status,
      factor_levels = factor_levels(column, variable_type),
      proposed_semantic_term = semantic_term(source, name),
      semantic_term_status = "proposed; review",
      review_status = if (
        nzchar(embedded_label) &&
        (nzchar(embedded_unit) || !(is.numeric(column) || inherits(column, "difftime")))
      ) "metadata recovered; review" else "manual review required",
      reviewer_notes = reviewer_note(source, name),
      stringsAsFactors = FALSE,
      check.names = FALSE
    )
  }
}

dictionary <- do.call(rbind, rows)
dir.create(dirname(output), recursive = TRUE, showWarnings = FALSE)
write.csv(dictionary, output, row.names = FALSE, na = "", fileEncoding = "UTF-8")
message(sprintf("Wrote %d unique source-variable rows to %s", nrow(dictionary), output))
