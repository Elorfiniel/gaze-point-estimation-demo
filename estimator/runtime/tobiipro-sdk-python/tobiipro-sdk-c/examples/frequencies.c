#include <stdlib.h>
#include <stdio.h>

#include "tobii_research_eyetracker.h"


void gaze_output_frequencies(TobiiResearchEyeTracker* eyetracker) {
  float initial_gaze_output_frequency;

  TobiiResearchStatus status = tobii_research_get_gaze_output_frequency(eyetracker, &initial_gaze_output_frequency);

  printf("The eye tracker's initial gaze output frequency is %f Hz with status %i.\n",
    initial_gaze_output_frequency, status);
  {
    TobiiResearchGazeOutputFrequencies* frequencies = NULL;
    size_t i = 0;
    status = tobii_research_get_all_gaze_output_frequencies(eyetracker, &frequencies);

    if (status == TOBII_RESEARCH_STATUS_OK) {
      for (; i < frequencies->frequency_count; i++) {
        status = tobii_research_set_gaze_output_frequency(eyetracker, frequencies->frequencies[i]);
        printf("Gaze output frequency set to %f Hz with status %i.\n", frequencies->frequencies[i], status);
      }
      tobii_research_set_gaze_output_frequency(eyetracker, initial_gaze_output_frequency);

      printf("Gaze output frequency reset to %f Hz.\n", initial_gaze_output_frequency);
    }
    else {
      printf("tobii_research_get_all_gaze_output_frequencies returned status %i.\n", status);
    }

    tobii_research_free_gaze_output_frequencies(frequencies);
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

  gaze_output_frequencies(eyetrackers->eyetrackers[eye_tracker_id]);

  return EXIT_SUCCESS;
}
