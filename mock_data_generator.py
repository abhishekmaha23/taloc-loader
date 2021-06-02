from faker import Faker
from faker.providers import BaseProvider
import pandas as pd
import random
import string
import datetime
import copy
import math

fake = Faker()

def get_new_personal_number():
    current_personal_number = 100001
    while True:
        yield current_personal_number
        current_personal_number += 1

possible_management_levels = ['FS I', 'FS II', 'FS IIIa', 'FS IIIb', 'FS IIIc', None]
possible_cost_centers = ['A', 'A1', 'B', 'C', 'D', 'E1', 'E2', 'F', 'G', 'H', 'J']
possible_organizations = [('A', 'Architecture'), ('WA', 'Public Sector'), ('TABC', 'Modeling'), ('TABD', 'Finance'), 
    ('TABA', 'Organic Electronics'), ('WABC', 'Asia Businss'), ('NABC', 'Packaging Tech'), ('WABC', 'Continuing Education'), 
    ('W', 'School of Management & Law'), ('LA', 'Terminology'), ('NABC', 'Analytical Tech'), ('NB', 'ABCD'), 
    ('NC', 'Pharma Tech'), ('VAB', 'Support')]
possible_employee_types = ['Dozierende 1', 'Dozierende 2', 'wiss. Mitarbeitende 1', 'wiss. Mitarbeitende 2', 'ATP 1']


class Person:
    def __init__(self, faker_instance) -> None:
        self.personal_number_before_2018 = ''
        self.personal_number = ''
        self.first_name = faker_instance.first_name()
        self.last_name = faker_instance.last_name()
        self.name = self.first_name + self.last_name
        self.date_of_birth = faker_instance.date_of_birth(minimum_age=20, maximum_age=80)
        self.birth_year = self.date_of_birth.year
        self.gender = random.choice(['Herr', 'Frau'])
    

class Employee(Person):
    def __init__(self, faker_instance) -> None:
        super().__init__(faker_instance)
        self.personal_number_before_2018 = str(get_new_personal_number())
        self.employment_number = str(random.randint(1, 9))
        self.personal_number = self.personal_number_before_2018 + '0' + self.employment_number
        self.abbreviation = (self.last_name[:3] + self.first_name[0]).lower()
        self.management_level = random.choice(possible_management_levels)
        self.cost_tax = '1234' + str(random.randint(1000, 9999))
        self.cost_center = 'Kost ' + random.choice(possible_cost_centers)
        self.organization_abbreviation, self.organization = random.choice(possible_organizations)
        self.employee_type = random.choice(possible_employee_types)
        if self.employee_type in ['Dozierende 1', 'Dozierende 2', 'ATP 1']:
            self.vertrags_bg = random.choice(['80.00', '100.00'])
        else:
            self.vertrags_bg = random.choice(['40.00', '60.00'])
        self.lohn_bg = self.vertrags_bg
        self.entry_date = faker_instance.date_between(end_date='-4y')
        self.end_date = '31-12-9999'


    def to_dataframe(self, target = None):
        # hr -till 2018 columns
        # Personalnummer bis 2018, Anstellungs-Nr,	PersNr,	Kurzzeich.,	Nachname,	Vorname,	Geb. Jahr,	
        # Anrede,	Kaderstufe,	Kostenst.,	Kostenstelle,	OEKürzel,	Organisationseinheit,	Mitarbeiterkreis,	
        # Vertrags-BG,	Lohn-BG,	Eintritt,	Austritt
        # hr -after 2018 columns
        # PersNr,	Kurzzeich.,	Nachname,	Vorname,	Geb. Jahr,	Anrede,	Kaderstufe,	Kostenst.,	Kostenstelle,	
        # OEKürzel,	Organisationseinheit,	Mitarbeiterkreis,	Vertrags-BG,	Lohn-BG,	Eintritt,	Austritt
        # will write files into both, by default
        hr_till_2018 = pd.DataFrame([self.personal_number_before_2018, self.employment_number, self.personal_number, 
            self.abbreviation, self.last_name, self.first_name, self.birth_year, self.gender, self.management_level, 
            self.cost_tax, self.cost_center, self.organization_abbreviation, self.organization, self.employee_type, 
            self.vertrags_bg, self.lohn_bg, self.entry_date, self.end_date])
        hr_after_2018 = pd.DataFrame([self.personal_number, self.abbreviation, self.last_name, self.first_name, 
            self.birth_year, self.gender, self.management_level, self.cost_tax, self.cost_center, self.organization_abbreviation, 
            self.organization, self.employee_type, self.vertrags_bg, self.lohn_bg, self.entry_date, self.end_date])

        if target is None:
            return hr_till_2018, hr_after_2018
        elif target == 'before-2018':
            return hr_till_2018
        elif target == 'after-2018':
            return hr_after_2018



def prepare_airport_data():
    # For flights, first identify valid airports
    # Airports
    airport_database = pd.read_csv('assets/airport-codes_csv.csv')
    # TODO - Test extension of airports list as well
    # airport_extension = pd.read_csv(f'{originals_folder}/{airports_ext}')
    # airport_database = pd.concat([airport_database_orig, airport_extension])
    airport_database = airport_database[airport_database['type'] != 'closed']
    airport_database = airport_database.rename(columns={'iso_country': 'country', 'municipality': 'city', 'iata_code': 'iata'})
    # Convert Ã¼ to ü etc.
    def try_unicode(str):
        try:
            return str.encode('latin1').decode('utf-8')
        except Exception:
            return str
    airport_database['country'] = airport_database.apply(
        lambda row: try_unicode(row['country']), axis=1)
    airport_database['city'] = airport_database.apply(
        lambda row: try_unicode(row['city']), axis=1)

    # Taking a small subset for the test cases which have IATA values - These IATA values might be needed for atmosfair.
    # Only considering large and medium airports- the others are good, but this might suffice for mock data generation. 
    airport_database = airport_database[(airport_database['type'] == 'large_airport') | (airport_database['type'] == 'medium_airport')]
    airport_database.dropna(subset=['iata'], inplace=True)

    return airport_database


airport_database = prepare_airport_data()

possible_flight_reasons = ['Conference', 'Unknown', 'Project Meeting', 'Strategic Collaborations', 'Committee Meetings']
possible_proveniences = ['AirplusCC', 'CWTravel']


def get_random_flight_number():
    letters = ''.join(random.choice(string.ascii_uppercase) for _ in range(2))
    numbers = str(random.randint(1000, 9999))
    return letters + numbers


class Flight:
    def __init__(self, faker_instance) -> None:
        self.number_of_segments = random.choice([1,2])
        self.airport_data = []
        self.to_flight_numbers = []
        self.return_flight_numbers = []
        # There's 3 nodes, 2 segments
        for _ in range(self.number_of_segments + 1):
            self.airport_data.append(airport_database.sample())        
        self.to_flight_dates = []
        self.return_flight_dates = []
        initial_to_flight_date = faker_instance.date_between(start_date='-4y', end_date='-1y')
        self.to_flight_dates.append(initial_to_flight_date)
        initial_return_flight_date = initial_to_flight_date + datetime.timedelta(days=random.randint(7, 10))
        self.return_flight_dates.append(initial_return_flight_date)
        # -1 because we're defining the start points of each segment of the journey here
        for _ in range(self.number_of_segments - 1):
            self.to_flight_dates.append(self.to_flight_dates[-1] + datetime.timedelta(days=random.randint(1, 3)))
            self.return_flight_dates.append(self.return_flight_dates[-1] + datetime.timedelta(days=random.randint(1, 3)))
        self.pax = random.choices([1, 2], weights=[0.95, 0.05])[0]


class Flight_Spesen_Airplus_Data(Flight):
    def __init__(self, faker_instance, passenger, data_type=None) -> None:
        super().__init__(faker_instance)
        if data_type is None:
            self.data_type = random.choice(['spesen', 'airplus'])
        else:
            self.data_type = data_type
        self.travel_class = random.choice(['Y', 'B'])
        self.aircraft = ''
        self.charter = ''
        self.flight_reason_other = ''
        self.flight_amount = str(round(random.uniform(50, 5000), 2))
        if self.data_type == 'spesen':
            self.flight_reason = random.choice(possible_flight_reasons)
            self.provenience = 'Archive'
            for _ in range(self.number_of_segments):
                # Get reasonable dates, and flight numbers
                # For simplifying, assuming that return flights start 10 days after initial flights
                self.to_flight_numbers.append(get_random_flight_number())
                self.return_flight_numbers.append(get_random_flight_number())
        elif self.data_type == 'airplus':
            self.flight_reason = ''
            self.provenience = random.choice(possible_proveniences)
        
        # Must associate one flying person to this flight. Will randomly sample from all 
        # flying people (guests, unregistered employees or otherwise).
        self.associated_passenger = passenger
        self.employee_name = self.associated_passenger.name
        self.employee_id_18 = self.associated_passenger.personal_number_before_2018
        self.employee_id_19 = self.associated_passenger.personal_number


        # Recording a random number of months before or after the date of starting the whole flight 
        record_date = self.to_flight_dates[0] + datetime.timedelta(months=random.randint(-4,4))        
        self.record_year = record_date.year
        self.record_month = record_date.month
        self.flight_date_unknown = 'FALSE'
        self.record_comments = ''
    
    def to_dataframe(self):
        pass


def get_new_dossier_number():
    current_dossier_number = 700001
    while True:
        yield current_dossier_number
        current_dossier_number += 1


def randomly_modify_passenger_name(first_name, last_name):
    modification_choice = random.choice([None, 'Reverse', 'Reverse+Slice', 'Slice'])
    if modification_choice == None:
        return first_name + ' ' + last_name
    elif modification_choice == 'Reverse':
        return last_name + ' ' + first_name
    elif modification_choice == 'Reverse+Slice':
        return last_name + ' ' + first_name[: random.randint(0, len(first_name))]
    elif modification_choice == 'Slice':
        return first_name[: random.randint(1, len(first_name))] + last_name


class Flight_BTA_Data(Flight):
    def __init__(self, faker_instance, passenger) -> None:
        super().__init__(faker_instance)
        self.profit_center = '9999'
        self.dossier_number = str(get_new_dossier_number())
        self.invoice_number = str(random.randint(1000000, 9999999))
        self.name = 'A Uni'
        self.department = random.choice(possible_organizations)[1]

        # Person chosen for the flight has to have weirdness randomly added.
        self.associated_passenger = passenger
        self.passenger_name = randomly_modify_passenger_name(self.associated_passenger.first_name, self.associated_passenger.last_name)

        self.pid_sales_amount = str(round(random.uniform(50, 5000), 2))
        self.ticket_no = str(random.random(10000, 99999))
        self.ticket_no_2 = str(random.random(10000, 99999))

        self.travel_class = random.choice(['Y', 'B', 'C'])
        self.metric_tons = str(random.uniform(0, 2))
        self.price = str(random.randint(1, 100)) + '.00'
        self.ext_reference_no =  str(random.random(10000, 99999))
        self.tkttkt =  str(random.random(10000, 99999))
        self.departure_date = self.to_flight_dates[0]
        self.check = 'OK'
        
        # routing values are weirdly formatted, and logic should be placed in the writing methods
        # Miles and kilometers are flight segment values as well, and need to modified accordingly.
        # self.miles = 'NA'
        # self.kilometers = 'NA'
    
    def to_dataframe(self):
        pass


possible_aircraft_types = ['Boeing 767-400 Passenger', 'Airbus A330-300', 'Fokker 100']

class AtmosfairData:
    def __init__(self, flight, faker_instance) -> None:
        self.associated_flight = flight
        # Departure, arrival, flight numbers, flight dates, travel class are from the flight object.
        self.pax = '1'
        self.aircraft = ''
        self.charter = ''
        self.uniqueID = ''
        self.unnamed = ''
        self.flight_column = 'ok'

        self.specific_fuel_consumption = str(random.uniform(1, 10))
        self.share_of_fuel_use_in_cruise = str(round(random.uniform(85, 100), 2)) + '%'
        self.fuel_use = random.uniform(0, 0.5)
        self.fuel_use_in_critical_alt = random.uniform(0.85, 1) * self.fuel_use
        self.CO2 = random.uniform(0, 1)
        self.CO2RFI2 = random.uniform(1, 1.5) * self.CO2
        self.CO2RFI27 = random.uniform(1, 1.5) * self.CO2RFI2
        self.CO2RFI4 = random.uniform(1, 1.5) * self.CO2RFI27
        self.CO2DEFRA = random.uniform(0, 2)
        self.CO2GHGGRI = random.uniform(0, 1)
        self.CO2ICAO = random.uniform(0, 1)
        self.CO2VFU = random.uniform(0, 1)
        self.aircraft1 = random.choice(possible_aircraft_types)
        # self.distance = 
        self.cruise_atitude = random.randint(100-300) * 100
        self.method = random.choice(['V2_2.16', 'V2_1_5'])
    
    def to_dataframe(self):
        pass

def generate_mock_data():

    num_people_overall = 50

    num_non_flying_employees = 30
    num_flying_employees = 14
    num_flying_guests = 3
    num_flying_employees_not_in_hr = 3

    list_non_flying_employees = []
    list_flying_employees = []
    list_flying_guests = []
    list_flying_employees_not_in_hr = []

    # Actually generating people
    for i in range(num_non_flying_employees):
        list_non_flying_employees.append(Employee(fake))
    for i in range(num_flying_employees):
        list_flying_employees.append(Employee(fake))
    for i in range(num_flying_guests):
        list_flying_guests.append(Person(fake))
    for i in range(num_flying_employees_not_in_hr):
        list_flying_employees_not_in_hr.append(Person(fake))
    list_all_flying_people = list_flying_employees + list_flying_employees_not_in_hr + list_flying_employees_not_in_hr


    # Every flying person needs to go to a flight booking.
    # We do this through shuffling the list and then iterating through it - no duplicates ensue.
    # Number of total flying people = number of total flights (round-trips)
    actual_passenger_list = random.shuffle(copy.deepcopy(list_all_flying_people))
    all_flights = []
    for passenger in actual_passenger_list:
        flight_type = random.choice(['bta', 'spesen', 'airplus'])
        if flight_type == 'bta':
            all_flights.append(Flight_BTA_Data(fake, passenger))
        elif flight_type == 'spesen':
            all_flights.append(Flight_Spesen_Airplus_Data(fake, passenger, 'spesen'))
        elif flight_type == 'airplus':
            all_flights.append(Flight_Spesen_Airplus_Data(fake, passenger, 'airplus'))

    # Control the proportion of flights that will have data in atmosfair reponse previously, and populate the CSV as needed.
    proportion_of_precached_atmosfair_data = 0.7
    num_flights_with_atmosfair_data = math.floor(len(all_flights) * proportion_of_precached_atmosfair_data)
    flights_with_atmosfair_data = random.shuffle(all_flights)[:num_flights_with_atmosfair_data]
    existing_atmosfair_data = []

    # Initialize Atmosfair data for all these flights

    for flight in flights_with_atmosfair_data:
        existing_atmosfair_data.append(AtmosfairData(flight, fake))


    # Begin writing all data to files.
    # for person in 