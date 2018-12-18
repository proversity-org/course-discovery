import logging

from analyticsclient.client import Client
from django.utils.functional import cached_property

from course_discovery.apps.course_metadata.data_loaders import AbstractDataLoader
from course_discovery.apps.course_metadata.models import CourseRun

logger = logging.getLogger(__name__)


class AnalyticsAPIDataLoader(AbstractDataLoader):

    API_TIMEOUT = 5  # time in seconds

    def __init__(self, partner, api_url, access_token=None, token_type=None, max_workers=None,
                 is_threadsafe=False, **kwargs):
        super(AnalyticsAPIDataLoader, self).__init__(
            partner, api_url, access_token, token_type, max_workers, is_threadsafe, **kwargs
        )

        # uuid: {course, count}
        self.course_dictionary = {}
        # uuid: {program, count}
        self.program_dictionary = {}

        if not (self.partner.analytics_url and self.partner.analytics_token):
            msg = 'Analytics API credentials are not properly configured for Partner [{partner}]!'.format(
                partner=partner.short_code)
            raise Exception(msg)

    @cached_property
    def api_client(self):

        analytics_api_client = Client(base_url=self.partner.analytics_url,
                                      auth_token=self.partner.analytics_token,
                                      timeout=self.API_TIMEOUT)

        return analytics_api_client

    def get_query_kwargs(self):
        return {}

    def ingest(self):
        """ Load data for all course runs. """
        course_summaries_response = self.api_client.course_summaries()
        course_run_summaries = course_summaries_response.course_summaries(fields=['course_id', 'count'])

        for course_run_summary in course_run_summaries:
            self._process_course_run_summary(course_run_summary=course_run_summary)

        for course_dict in self.course_dictionary.values():
            self._process_course_enrollment_count(course_dict['course'], course_dict['count'])

        for program_dict in self.program_dictionary.values():
            # update program count
            # Remove after testing of updated refresh
            logger.info(program_dict)

    def _process_course_run_summary(self, course_run_summary):
        # get course run from course key
        course_run = None
        course_run_key = course_run_summary['course_id']
        course_run_count = course_run_summary['count']
        try:
            course_run = CourseRun.objects.get(key__iexact=course_run_key)
        except CourseRun.DoesNotExist:
            logger.info('Course run: [{course_run_key}] not found in DB.'.format(course_run_key=course_run_key))
            return

        course = course_run.course
        # update course run count
        # course_run.count = course_run_count
        # course_run.save()
        # logger.info('Updating course run')
        # get course for course run

        # add course run total to course total in dictionary
        if course.uuid in self.course_dictionary:
            # Remove after testing of updated refresh
            logger.info('incrementing from {old_count} to {new_count}'.format(
                old_count=self.course_dictionary[course.uuid]['count'],
                new_count=self.course_dictionary[course.uuid]['count'] + course_run_count))
            self.course_dictionary[course.uuid]['count'] += course_run_count
        else:
            # Remove after testing of updated refresh
            # logger.info('setting to {count}'.format(count=course_run_count))
            self.course_dictionary[course.uuid] = {'course': course, 'count': course_run_count}

    def _process_course_enrollment_count(self, course, count):
        # update course count
        # course.count = count
        # course.save()
        # logger.info('Updating course')
        # Add course count to program dictionary for all programs
        for program in course.programs.all():
            logger.info(program.title)

            # add course total to program total in dictionary
            if program.uuid in self.program_dictionary:
                # Remove after testing of updated refresh
                logger.info('incrementing from {old_count} to {new_count}'.format(
                    old_count=self.program_dictionary[program.uuid]['count'],
                    new_count=self.program_dictionary[program.uuid]['count'] + count))
                self.program_dictionary[program.uuid]['count'] += count
            else:
                # Remove after testing of updated refresh
                # logger.info('setting to {count}'.format(count=count))
                self.program_dictionary[program.uuid] = {'program': program, 'count': count}
