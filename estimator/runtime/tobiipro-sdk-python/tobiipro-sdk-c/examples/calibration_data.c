#include <stdio.h>
#include <stdlib.h>

#include "tobii_research_eyetracker.h"


void calibration_data(TobiiResearchEyeTracker* eyetracker) {

  /* Save the calibration to file. */
  char* filename = "saved_calibration.bin";
  char* serial_number = NULL;

  FILE* f = fopen(filename, "wb");

  TobiiResearchCalibrationData* calibration_data = NULL;
  TobiiResearchStatus status = tobii_research_retrieve_calibration_data(eyetracker, &calibration_data);

  if (status != TOBII_RESEARCH_STATUS_OK)
    return;

  tobii_research_get_serial_number(eyetracker, &serial_number);

  /* None is returned on empty calibration. */
  if (calibration_data->size != 0) {

    printf("Saving calibration to file for eye tracker with serial number %s.\n", serial_number);
    fwrite(calibration_data->data, calibration_data->size, 1, f);
  }
  else {
    printf("No calibration available for eye tracker with serial number %s.\n", serial_number);
  }

  fclose(f);
  tobii_research_free_calibration_data(calibration_data);


  {
    /* Read the calibration from file. */
    FILE* calibration_file = fopen(filename, "rb");
    size_t file_size;
    if (!calibration_file) {
      printf("Calibration file not found!\n");
      return;
    }

    fseek(calibration_file, 0, SEEK_END);
    file_size = (size_t)ftell(calibration_file);

    rewind(calibration_file);

    if (file_size <= 0) {
      printf("Calibration file is empty!\n");
      return;
    };

    TobiiResearchCalibrationData calibration_data_to_write;

    calibration_data_to_write.data = malloc(file_size);
    calibration_data_to_write.size = file_size;

    file_size = fread(calibration_data_to_write.data, calibration_data_to_write.size, 1, calibration_file);

    /* Don't apply empty calibrations. */
    if (file_size > 0) {
      printf("Applying calibration on eye tracker with serial number %s.\n", serial_number);
      tobii_research_apply_calibration_data(eyetracker, &calibration_data_to_write);
    }
    free(calibration_data_to_write.data);
    tobii_research_free_string(serial_number);
    fclose(calibration_file);
  }
}


int main(int argc, char* argv[]) {

  /** Parse eye tracker ID from command line arguments. */
  if (argc < 2) {
    printf("Usage: calibration.exe <eye_tracker_id>\n");
    return EXIT_FAILURE;
  }

  /** Find all available eye trackers. */
  TobiiResearchEyeTrackers* eyetrackers = NULL;

  TobiiResearchStatus result;
  size_t i = 0;

  result = tobii_research_find_all_eyetrackers(&eyetrackers);
  if (result != TOBII_RESEARCH_STATUS_OK) {
    printf("Finding trackers failed. Error: %d\n", result);
    return result;
  }

  /** Calibrate the eye tracker with the matched ID. */
  int eye_tracker_id = atoi(argv[1]);
  if (eye_tracker_id < 0 || eye_tracker_id >= eyetrackers->count) {
    printf("Eye tracker ID %d is out of range. There are %zu trackers available.\n", eye_tracker_id, eyetrackers->count);
    return EXIT_FAILURE;
  }

  calibration_data(eyetrackers->eyetrackers[eye_tracker_id]);

  return EXIT_SUCCESS;
}
