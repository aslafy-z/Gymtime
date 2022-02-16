import time
import datetime
from api import basic_fit_api
from sys import exit as sys_exit
import configargparse


class Gymtime:
    ''' Gymtime class implements the booking flow '''

    # User information
    user = None
    open_reservations = 0
    reservation = None
    session = None
    availability = []
    date_for_booking = None

    # Constants
    max_gym_duration = 90
    max_open_reservations = 2

    def __init__(self, username: str, password: str, book_at_date: datetime.date, book_at_time: datetime.time, interval: int):
        #  Add arguments from CLI
        self.username = username
        self.password = password
        self.book_at_time = book_at_time
        self.book_at_date = book_at_date
        self.interval = interval
        # Create a new session for the user
        self.session = self.login()
        # Create a reservation
        self.start_new_booking()
        # Finished! Wrap everything up
        self.inform_about_reservation()

    def start_new_booking(self):
        ''' Initiate a new booking request '''
        try:
            # Get user information for a personalised CLI experience
            self.user = basic_fit_api.get_member_information(self.session)
            # Get the amount of open reservations
            self.open_reservations = basic_fit_api.get_open_reservations(self.session)
            # Check if it's possible to reserve more
            if len(self.open_reservations) >= self.max_open_reservations:
                raise Exception('Maximum amount of bookings already')
            # Give the user feedback that everything is OK
            self.say_hi()
            # Parse the time
            self.parse_time_for_booking()
            # Lets the to book
            self.try_to_make_reservation()
        except Exception as error:
            print(error)
            sys_exit(1)

    def say_hi(self):
        ''' Give a little love to the member '''
        print('Hi {}, I selected {} as your gym, you have {} open booking(s):'.format(
            self.user['first_name'],
            self.user['favorite_club']['name'],
            len(self.open_reservations))
        )
        for booking in self.open_reservations:
            start_datetime = datetime.datetime.fromisoformat(booking['startDateTime'])
            print('- {} ({} minutes) at {} club'.format(
                datetime.datetime.strftime(start_datetime, '%Y-%m-%d %H:%M'),
                booking['duration'],
                booking['clubName'],
            ))

    def parse_time_for_booking(self):
        '''  Try to parse the date to a workable format '''
        try:
            if self.book_at_time.minute % 15 != 0:
                raise Exception()
            self.date_for_booking = datetime.datetime.combine(
                self.book_at_date, self.book_at_time)
        except Exception:
            print('Time format is invalid, use something like: 10:00 or 11:45')
            sys_exit(1)

    def try_to_make_reservation(self):
        ''' Checks if there's a session available for the date '''
        # Fetch the availability for favourite gym
        self.availability = basic_fit_api.get_available_times_for_members_favourite_club(
            self.session,
            self.user,
            self.date_for_booking
        )
        # Quick check for availability
        if len(self.availability) == 0:
            raise Exception(
                'There are no more sessions available on this date')
        # Check all policy's
        for policy in self.availability:
            # Parse the date string to a workable format
            # session_date = datetime.strptime(
            #     policy['startDateTime'], '%Y-%m-%dT%H:%M:%S.%f')
            session_date = datetime.datetime.fromisoformat(policy['startDateTime'])
            # Check for the specific time
            if session_date.time() == self.date_for_booking.time():
                # Create the reservation
                return basic_fit_api.create_reservation(
                    self.session,
                    self.user['favorite_club'],
                    policy,
                    self.max_gym_duration
                )
        # Preferred time is unavailable
        self.retry_to_book_preferred_time()

    def retry_to_book_preferred_time(self):
        ''' Fully booked at specified time '''
        print('{} seems to be fully booked at {}'.format(
            self.user['favorite_club']['name'], self.book_at_time))
        print('I will retry in {} seconds'.format(self.interval))
        try:
            time.sleep(self.interval)
        except KeyboardInterrupt:
            print('\nExiting...')
            sys_exit(0)
        self.try_to_make_reservation()

    def login(self):
        ''' Creates a new session '''
        try:
            # Try to get the JWT token from Basic Fit
            jwt_token = basic_fit_api.get_jwt_from_credentials(
                self.username, self.password)
            # Exchange JWT token for Cookie
            return basic_fit_api.exchange_jwt_for_session(jwt_token)
        except Exception as error:
            sys_exit(error)

    def inform_about_reservation(self):
        print(
            "Your reservation for {} at {} is confirmed! You'll receive an email from Basic-Fit any second.".format(
                self.date_for_booking.strftime('%d-%m-%Y %H:%M'),
                self.user['favorite_club']['name']
            )
        )


def main():
    ''' Entrypoint. Parse arguments and start up the booking process. '''
    parser = configargparse.ArgParser()
    parser.add_argument('-u', '--username', dest='username', required=True,
                        env_var='BASICFIT_EMAIL', help='E-mail used for your Basic-Fit account')
    parser.add_argument('-p', '--password', dest='password', required=True,
                        env_var='BASICFIT_PASSWORD', help='Password used for your Basic-Fit account')
    parser.add_argument('-d', '--date', dest='date', required=True, type=datetime.date.fromisoformat,
                        help='Date for the reservations (yyyy-mm-dd)')
    parser.add_argument('-t', '--time', dest='time',
                        required=True, type=datetime.time.fromisoformat, help='Time for the reservations (hh:mm)')
    parser.add_argument('-i', '--interval', dest='interval', type=int,
                        help='Interval in seconds before retrying again', default=30)
    args = parser.parse_args()

    Gymtime(
        args.username,
        args.password,
        args.date,
        args.time,
        args.interval
    )


main()
