#include <stdlib.h>
#include <stdio.h>

#include <windows.h>

#include "tobii_research_eyetracker.h"
#include "tobii_research_calibration.h"


static void sleep_ms(int time) {
  Sleep(time);
}


void calibration(TobiiResearchEyeTracker* eyetracker) {

  /** Enter calibration mode. */
  TobiiResearchStatus status = tobii_research_screen_based_calibration_enter_calibration_mode(eyetracker);
  char* serial_number = NULL;
  tobii_research_get_serial_number(eyetracker, &serial_number);
  printf("Entered calibration mode for eye tracker with serial number %s .\n", serial_number);
  tobii_research_free_string(serial_number);

  /**
   * Define the points on screen we should calibrate at. The coordinates are
   * normalized, i.e. (0.0, 0.0) is the upper left corner and (1.0, 1.0) is
   * the lower right corner.
   */
  {
#define NUM_OF_POINTS  5U

    TobiiResearchNormalizedPoint2D points_to_calibrate[NUM_OF_POINTS] = \
      {{0.5f, 0.5f}, { 0.1f, 0.1f }, { 0.1f, 0.9f }, { 0.9f, 0.1f }, { 0.9f, 0.9f }};
    size_t i = 0;

    for (; i < NUM_OF_POINTS; i++) {
      TobiiResearchNormalizedPoint2D* point = &points_to_calibrate[i];
      printf("Show a point on screen at (%f,%f).\n", point->x, point->y);

      /** Wait a little for user to focus. */
      sleep_ms(700);

      printf("Collecting data at (%f,%f).\n", point->x, point->y);
      if (tobii_research_screen_based_calibration_collect_data(eyetracker, point->x, point->y) != TOBII_RESEARCH_STATUS_OK) {
        /**
         * Try again if it didn't go well the first time. Not all eye tracker
         * models will fail at this point, but instead fail on ComputeAndApply.
         */
        tobii_research_screen_based_calibration_collect_data(eyetracker, point->x, point->y);
      }
    }

    printf("Computing and applying calibration.\n");
    TobiiResearchCalibrationResult* calibration_result = NULL;
    status = tobii_research_screen_based_calibration_compute_and_apply(eyetracker, &calibration_result);

    if (status == TOBII_RESEARCH_STATUS_OK && calibration_result->status == TOBII_RESEARCH_CALIBRATION_SUCCESS) {
      printf("Compute and apply returned %i and collected at %zu points.\n", status, calibration_result->calibration_point_count);
    }
    else {
      printf("Calibration failed!\n");
    }

    /** Free calibration result when done using it */
    tobii_research_free_screen_based_calibration_result(calibration_result);

    /** Analyze the data and maybe remove points that weren't good. */
    TobiiResearchNormalizedPoint2D* recalibrate_point = &points_to_calibrate[1];
    printf("Removing calibration point at (%f,%f).\n", recalibrate_point->x, recalibrate_point->y);
    status = tobii_research_screen_based_calibration_discard_data(eyetracker, recalibrate_point->x, recalibrate_point->y);

    /** Redo collection at the discarded point */
    printf("Show a point on screen at (%f,%f).\n", recalibrate_point->x, recalibrate_point->y);
    tobii_research_screen_based_calibration_collect_data(eyetracker, recalibrate_point->x, recalibrate_point->y);

    /** Compute and apply again. */
    printf("Computing and applying calibration.\n");
    status = tobii_research_screen_based_calibration_compute_and_apply(eyetracker, &calibration_result);

    if (status == TOBII_RESEARCH_STATUS_OK && calibration_result->status == TOBII_RESEARCH_CALIBRATION_SUCCESS) {
      printf("Compute and apply returned %i and collected at %zu points.\n", status, calibration_result->calibration_point_count);
    }
    else {
      printf("Calibration failed!\n");
    }

    /** Free calibration result when done using it */
    tobii_research_free_screen_based_calibration_result(calibration_result);
    /** See that you're happy with the result. */
  }

  /** The calibration is done. Leave calibration mode. */
  status = tobii_research_screen_based_calibration_leave_calibration_mode(eyetracker);

  printf("Left calibration mode.\n");
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

  calibration(eyetrackers->eyetrackers[eye_tracker_id]);

  return EXIT_SUCCESS;
}
