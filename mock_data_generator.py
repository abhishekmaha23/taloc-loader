from faker import Faker
from faker.providers import BaseProvider
import pandas as pd
import random
import string
import datetime
import copy
import math
import uuid
import shutil
import os
from openpyxl import load_workbook


fake = Faker()

def get_new_personal_number():
    current_personal_number = 100001
    while True:
        yield current_personal_number
        current_personal_number += 1

personal_number_generator = get_new_personal_number()

possible_management_levels = ['FS I', 'FS II', 'FS IIIa', 'FS IIIb', 'FS IIIc', None]
possible_cost_centers = ['A', 'A1', 'B', 'C', 'D', 'E1', 'E2', 'F', 'G', 'H', 'J']
possible_organizations = [('A', 'Architecture'), ('WA', 'Public Sector'), ('TABC', 'Modeling'), ('TABD', 'Finance'), 
    ('TABA', 'Organic Electronics'), ('WABC', 'Asia Businss'), ('NABC', 'Packaging Tech'), ('WABC', 'Continuing Education'), 
    ('W', 'School of Management & Law'), ('LA', 'Terminology'), ('NABC', 'Analytical Tech'), ('NB', 'ABCD'), 
    ('NC', 'Pharma Tech'), ('VAB', 'Support')]
possible_employee_types = ['Dozierende 1', 'Dozierende 2', 'wiss. Mitarbeitende 1', 'wiss. Mitarbeitende 2', 'ATP 1']

hr_before_2019_columns = ('Personalnummer bis 2018', 'Anstellungs-Nr',	'PersNr',	'Kurzzeich.',	'Nachname',	'Vorname',	'Geb. Jahr', 'Anrede',	'Kaderstufe',	'Kostenst.',	'Kostenstelle',	'OEKürzel',	'Organisationseinheit',	'Mitarbeiterkreis', 'Vertrags-BG',	'Lohn-BG',	'Eintritt',	'Austritt')
hr_since_2019_columns = ('PersNr',	'Kurzzeich.',	'Nachname',	'Vorname',	'Geb. Jahr', 'Anrede',	'Kaderstufe',	'Kostenst.',	'Kostenstelle',	'OEKürzel',	'Organisationseinheit',	'Mitarbeiterkreis', 'Vertrags-BG',	'Lohn-BG',	'Eintritt',	'Austritt')

class Person:
    def __init__(self, faker_instance) -> None:
        self.personal_number_before_2019 = ''
        self.personal_number = ''
        self.gender = random.choice(['Herr', 'Frau'])
        if self.gender == 'Herr':
            self.first_name = faker_instance.first_name_male()
            self.last_name = faker_instance.last_name_male()
        else:
            self.first_name = faker_instance.first_name_female()
            self.last_name = faker_instance.last_name_female()
        
        self.name = self.first_name + ' ' + self.last_name
        self.date_of_birth = faker_instance.date_of_birth(minimum_age=20, maximum_age=80)
        self.birth_year = self.date_of_birth.year
        
    

class Employee(Person):
    def __init__(self, faker_instance) -> None:
        super().__init__(faker_instance)
        self.personal_number_before_2019 = str(next(personal_number_generator))
        self.employment_number = str(random.randint(1, 9))
        self.personal_number = self.personal_number_before_2019 + '0' + self.employment_number
        # self.abbreviation = (self.last_name[:3] + self.first_name[0]).lower()
        self.abbreviation = str(uuid.uuid4())[:8] # Not optimal, but chances of collision are negligible in scales of 10k.
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
        self.entry_date = faker_instance.date_between(end_date='-4y').strftime('%d-%m-%Y') + ' 00:00:00'
        self.end_date = '9999-12-31 00:00:00' 
        self._make_dataframes()


    def _make_dataframes(self):
        # hr -before 2019 columns
        # Personalnummer bis 2018, Anstellungs-Nr,	PersNr,	Kurzzeich.,	Nachname,	Vorname,	Geb. Jahr,	
        # Anrede,	Kaderstufe,	Kostenst.,	Kostenstelle,	OEKürzel,	Organisationseinheit,	Mitarbeiterkreis,	
        # Vertrags-BG,	Lohn-BG,	Eintritt,	Austritt
        # hr -since 2019 columns
        # PersNr,	Kurzzeich.,	Nachname,	Vorname,	Geb. Jahr,	Anrede,	Kaderstufe,	Kostenst.,	Kostenstelle,	
        # OEKürzel,	Organisationseinheit,	Mitarbeiterkreis,	Vertrags-BG,	Lohn-BG,	Eintritt,	Austritt
        # will write files into both, by default
        self.hr_before_2019 = pd.DataFrame([self.personal_number_before_2019, self.employment_number, self.personal_number, 
            self.abbreviation, self.last_name, self.first_name, self.birth_year, self.gender, self.management_level, 
            self.cost_tax, self.cost_center, self.organization_abbreviation, self.organization, self.employee_type, 
            self.vertrags_bg, self.lohn_bg, self.entry_date, self.end_date]).T
        self.hr_before_2019.columns = hr_before_2019_columns    
        self.hr_since_2019 = pd.DataFrame([self.personal_number, self.abbreviation, self.last_name, self.first_name, 
            self.birth_year, self.gender, self.management_level, self.cost_tax, self.cost_center, self.organization_abbreviation, 
            self.organization, self.employee_type, self.vertrags_bg, self.lohn_bg, self.entry_date, self.end_date]).T
        self.hr_since_2019.columns = hr_since_2019_columns
    
    
    def get_dataframe(self, target):        
        if target == 'before-2019':
            return self.hr_before_2019
        elif target == 'since-2019':
            return self.hr_since_2019



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


def get_random_flight_number(type=None):
    airline_designator = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(2))
    flight_designator = str(random.randint(1, 9999))
    if type == 'bta':
        optional_character_1 = random.choice(string.ascii_uppercase)
        optional_character_2 = random.choice(string.ascii_uppercase)
        flight_number = airline_designator + optional_character_1 + flight_designator + optional_character_2
        return (airline_designator, flight_designator, optional_character_1, optional_character_2, flight_number)
    else:
        optional_character_1 = random.choice(['', random.choice(string.ascii_uppercase)])
        optional_character_2 = random.choice(['', random.choice(string.ascii_uppercase)])
        return airline_designator + optional_character_1 + flight_designator + optional_character_2


class Flight:
    def __init__(self, faker_instance) -> None:
        self.number_of_segments = random.choice([1,2])
        self.airport_data = []
        self.to_flight_numbers = []
        self.return_flight_numbers = []
        # There's 3 nodes, 2 segments
        for _ in range(self.number_of_segments + 1):
            self.airport_data.append(airport_database.sample())
        self.to_segment_endpoints = []
        self.return_segment_endpoints = []

        for i in range(self.number_of_segments):
            self.to_segment_endpoints.append((self.airport_data[i].iata.iloc[0], self.airport_data[i+1].iata.iloc[0]))
            self.return_segment_endpoints.insert(0, (self.airport_data[i+1].iata.iloc[0], self.airport_data[i].iata.iloc[0]))
        
        self.all_segment_endpoint_tuples = self.to_segment_endpoints + self.return_segment_endpoints
       
        # For simplifying, assuming that return flights start 10 days after initial flights
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
        
        self.all_flight_dates = self.to_flight_dates + self.return_flight_dates
        
        self.pax = random.choices([1, 2, 3, 4, 5, 6, 7], weights=[0.90, 0.04, 0.01, 0.01, 0.01, 0.01, 0.01])[0]


flights_spesen_airplus_columns = ['departure',	'arrival', 'pax',	'travelClass', 'flightNumber', 'flightDate', 'aircraft', 
    'charter', 'flightReason', 'flightReasonOther', 'employeeName', 'employeeID18',	'employeeID19', 'FlightAmount', 'recordYear',	
    'recordMonth', 'flightDateUnknown', 'recordComments', 'provenience']

class Flight_Spesen_Airplus_Data(Flight):
    def __init__(self, faker_instance, passenger, data_type=None) -> None:
        super().__init__(faker_instance)
        if data_type is None:
            self.data_type = random.choice(['spesen', 'airplus'])
        else:
            self.data_type = data_type
        self.travel_class = random.choice(['Y', 'B', 'F'])
        self.aircraft = ''
        self.charter = ''
        self.flight_reason_other = ''
        self.flight_amount = str(round(random.uniform(50, 5000), 2))
        if self.data_type == 'spesen':
            self.flight_reason = random.choice(possible_flight_reasons)
            self.provenience = 'Archive'
            for _ in range(self.number_of_segments):
                # Get reasonable dates, and flight numbers
                self.to_flight_numbers.append(get_random_flight_number())
                self.return_flight_numbers.append(get_random_flight_number())
            self.all_flight_numbers = self.to_flight_numbers + self.return_flight_numbers
        elif self.data_type == 'airplus':
            self.flight_reason = ''
            self.provenience = random.choice(possible_proveniences)
            self.all_flight_numbers  = ['' for i in range(2 * self.number_of_segments)]
        # Must associate one flying person to this flight. Will randomly sample from all 
        # flying people (guests, unregistered employees or otherwise).
        self.associated_passenger = passenger
        self.employee_name = self.associated_passenger.name
        self.employee_id_18 = self.associated_passenger.personal_number_before_2019
        self.employee_id_19 = self.associated_passenger.personal_number


        # Recording a random number of months before or after the date of starting the whole flight 
        record_date = self.to_flight_dates[0] + datetime.timedelta(weeks=random.randint(-16,16))
        self.record_year = record_date.year
        self.record_month = record_date.month
        self.flight_date_unknown = 'False'
        self.record_comments = ''

        self._make_dataframe()

    def _make_dataframe(self):
        # columns departure	arrival	pax	travelClass	flightNumber	flightDate	aircraft	charter	flightReason	flightReasonOther	employeeName	employeeID18	employeeID19	FlightAmount	recordYear	recordMonth	flightDateUnknown	recordComments	provenience
        indices = list(range(len(self.to_flight_numbers) + len(self.return_flight_numbers)))
        self.flight_df = pd.DataFrame(columns=flights_spesen_airplus_columns, index=indices)
        current_row = 0
        for i in range(len(self.all_segment_endpoint_tuples)):
            row_df = [self.all_segment_endpoint_tuples[i][0], self.all_segment_endpoint_tuples[i][1], self.pax, self.travel_class, 
                self.all_flight_numbers[i], self.all_flight_dates[i].strftime("%d-%m-%Y"), self.aircraft, self.charter, self.flight_reason, 
                self.flight_reason_other, self.employee_name, self.employee_id_18, self.employee_id_19, self.flight_amount,
                self.record_year, self.record_month, self.flight_date_unknown, self.record_comments, self.provenience]
            self.flight_df.loc[current_row] = row_df
            current_row += 1


    def get_dataframe(self):
        return self.flight_df


def get_new_dossier_number():
    current_dossier_number = 700001
    while True:
        yield current_dossier_number
        current_dossier_number += 1

dossier_number_generator = get_new_dossier_number()

def randomly_modify_passenger_name(first_name, last_name):
    modification_choice = random.choice([None, 'Reverse', 'Reverse+Slice', 'Slice'])
    if modification_choice == None:
        return first_name + ' ' + last_name
    elif modification_choice == 'Reverse':
        return last_name + ' ' + first_name
    elif modification_choice == 'Reverse+Slice':
        return last_name + ' ' + first_name[: random.randint(0, len(first_name))]
    elif modification_choice == 'Slice':
        return first_name[: random.randint(1, len(first_name))] + ' ' + last_name

flights_bta_columns = ['Profit Center', 'Dossier No', 'Invoice Receiver', 'Name', 'Department', 'Pax', 
    'PID sales amount', 'Ticket N°', 'Ticket N°2', 'From Destination', 'To Destination','Class', 'Metric Tons',
    'Price', 'Airline Miles', 'Airline Km', 'Departure Date', 'Ext. Reference N°', 'TKTTKT', 'check', 'Routing 1', 
    'Routing 2', 'Routing 3', 'Routing 4', 'Routing 5', 'Routing 6', 'Routing 7', 'Routing 8', 'Routing 9', 'Routing 10',
    'Routing 11', 'Routing 12']

# Taken departments from bta_legs_import.py
possible_bta_deps = {
    'Life Sciences & Facility Managment': 'N',
    'Departement Angewandte Linguistik': 'L',
    'Departement Gesundheit': 'G',
    'School of Management and Law': 'W',
    'Rektorat': 'R',
    'Departement Soziale Arbeit': 'S',
    'School of Engineering': 'T',
    'Departement Angewandte Psychologie': 'P',
    'Finanzen & Services': 'V'
}
# Taken possible fare classes from bta_legs_import.py
possible_bta_fare_classes = ['F', 'Y', 'C', 'W']


class Flight_BTA_Data(Flight):
    def __init__(self, faker_instance, passenger) -> None:
        super().__init__(faker_instance)
        self.profit_center = '9999'
        self.dossier_number = str(next(dossier_number_generator))
        self.invoice_number = str(random.randint(1000000, 9999999))
        self.name = 'A Uni'
        self.department = random.choice(list(possible_bta_deps.keys()))

        # Person chosen for the flight has to have weirdness randomly added.
        self.associated_passenger = passenger
        self.passenger_name = randomly_modify_passenger_name(self.associated_passenger.first_name, self.associated_passenger.last_name)

        self.pid_sales_amount = str(round(random.uniform(50, 5000), 2)) # only for first expense, 0 for rest.
        self.pid_sales_amount_list = [self.pid_sales_amount] + ['0.00' for _ in range(len(self.all_segment_endpoint_tuples) - 1)]
        
        self.ticket_no = str(random.randint(10000, 99999))
        self.ticket_no_2 = str(random.randint(10000, 99999))

        self.travel_class = random.choice(['F', 'Y', 'C', 'W'])
        self.metric_tons_list =  [] # str(random.uniform(0, 2))
        for _ in self.to_segment_endpoints:
            self.metric_tons_list.append(str(round(random.uniform(0, 2), 2)))
        self.metric_tons_list = self.metric_tons_list + list(reversed(self.metric_tons_list))
        
        self.price_list = [] # str(random.randint(1, 100)) + '.00'
        for _ in self.to_segment_endpoints:
            self.price_list.append(str(random.randint(1, 100)) + '.00')
        self.price_list = self.price_list + list(reversed(self.price_list))

        self.miles_list = []
        for _ in self.to_segment_endpoints:
            self.miles_list.append(random.uniform(100, 6000))        
        self.miles_list = self.miles_list + list(reversed(self.miles_list))
        self.kilometers_list = [x* 1.6 for x in self.miles_list]
        
        self.miles_list = [str(round(x, 2)) for x in self.miles_list]
        self.kilometers_list = [str(round(x, 2)) for x in self.kilometers_list]

        self.departure_date = self.to_flight_dates[0]
        self.ext_reference_no =  str(random.randint(10000, 99999))
        self.tkttkt =  str(random.randint(10000, 99999))
        self.check = 'OK'
        
        self.all_flight_numbers = []
        # routing values are weirdly formatted as follows
        self.routing_columns = ['' for i in range(12)]
        for i in range(len(self.all_segment_endpoint_tuples)):
            flight_details_tuple = get_random_flight_number(type='bta')
            # Format - ['from' | 'to'| 'airline'| 'nr'| 'class orig'| 'class'| 'leg_date']
            routing_string = self.all_segment_endpoint_tuples[i][0] + ' |' + self.all_segment_endpoint_tuples[i][1] \
                    + ' |' + flight_details_tuple[0] + ' | ' + flight_details_tuple[1] + '|' + flight_details_tuple[2] + '|'  \
                    + self.travel_class + '|' + self.all_flight_dates[i].strftime('%d.%m.%Y')
            self.routing_columns[i] = routing_string
            self.all_flight_numbers.append(flight_details_tuple[4])
        
        self._make_dataframe()

    def _make_dataframe(self):
        # Profit Center	Dossier No	Invoice Receiver	Name	Department	Pax	PID sales amount	Ticket N°	Ticket N°2	From Destination	To Destination	Class	Metric Tons	Price	Airline Miles	Airline Km	Departure Date	Ext. Reference N°	TKTTKT	check	Routing 1	Routing 2	Routing 3	Routing 4	Routing 5	Routing 6	Routing 7	Routing 8	Routing 9	Routing 10	Routing 11	Routing 12
        indices = list(range(len(self.to_flight_numbers) + len(self.return_flight_numbers)))
        self.flight_df = pd.DataFrame(columns=flights_bta_columns, index=indices)
        current_row = 0
        for i in range(len(self.all_segment_endpoint_tuples)):
            row_df = [self.profit_center, self.dossier_number, self.invoice_number, self.name, self.department, self.passenger_name, 
                self.pid_sales_amount_list[i], self.ticket_no, self.ticket_no_2, self.all_segment_endpoint_tuples[i][0], 
                self.all_segment_endpoint_tuples[i][1], self.travel_class, self.metric_tons_list[i], self.price_list[i], 
                self.miles_list[i], self.kilometers_list[i], self.departure_date, self.ext_reference_no,self.tkttkt, self.check, 
                self.routing_columns[0], self.routing_columns[1], self.routing_columns[2], self.routing_columns[3], self.routing_columns[4], 
                self.routing_columns[5], self.routing_columns[6], self.routing_columns[7], self.routing_columns[8], self.routing_columns[9],
                self.routing_columns[10], self.routing_columns[11]
                ]
            # print(len(row_df))
            # print(len(flights_bta_columns))
            self.flight_df.loc[current_row] = row_df
            current_row += 1
    
    def get_dataframe(self):
        return self.flight_df



possible_aircraft_types = ['Boeing 767-400 Passenger', 'Airbus A330-300', 'Fokker 100']

atmosfair_data_columns = ['departure', 'arrival', 'pax', 'travelClass', 'flightNumber', 'flightDate','aircraft', 'charter', 
    'UniqueID atmosfair', 'Unnamed: 11', 'flight', 'specific fuel consumption', 'share of fuel use in cruise', 'fuel use', 	
    'fuel use in critical altitudes', 'CO2', 'CO2RFI2', 'CO2RFI2.7', 'CO2RFI4', 'CO2DEFRA', 'CO2GHGGRI', 'CO2ICAO', 'CO2VFU',
    'aircraft.1', 'distance','cruise altitude', 'method']

class AtmosfairFlightData:
    def __init__(self, flight, faker_instance) -> None:
        self.associated_flight = flight
        # Departure, arrival, flight numbers, flight dates, travel class are from the flight object.
        self.pax = '1'
        self.aircraft = ''
        self.charter = ''
        self.uniqueID = ''
        self.unnamed = ''
        self.flight_column = 'ok'
        num_segments = len(self.associated_flight.to_segment_endpoints)
        self.specific_fuel_consumption_list = [str(random.uniform(1, 10)) for _ in range(2*num_segments)]
        self.share_of_fuel_use_in_cruise_list = [str(round(random.uniform(85, 100), 2)) + '%' for _ in range(2*num_segments)]
        self.fuel_use_list = [random.uniform(0, 0.5) for _ in range(2*num_segments)]
        self.fuel_use_in_critical_alt_list = [random.uniform(0.85, 1) * self.fuel_use_list[i] for i in range(2*num_segments)]
        self.CO2_list = [random.uniform(0, 1) for _ in range(2*num_segments)]
        self.CO2RFI2_list = [random.uniform(1, 1.5) * self.CO2_list[i] for i in range(2*num_segments)]
        self.CO2RFI27_list = [random.uniform(1, 1.5) * self.CO2RFI2_list[i] for i in range(2*num_segments)]
        self.CO2RFI4_list = [random.uniform(1, 1.5) * self.CO2RFI27_list[i] for i in range(2*num_segments)]
        self.CO2DEFRA_list = [random.uniform(0, 2) for _ in range(2*num_segments)]
        self.CO2GHGGRI_list = [random.uniform(0, 1) for _ in range(2*num_segments)]
        self.CO2ICAO_list = [random.uniform(0, 1) for _ in range(2*num_segments)]
        self.CO2VFU_list = [random.uniform(0, 1) for _ in range(2*num_segments)]
        self.aircraft1_list = self._duplicate_with_reversal([random.choice(possible_aircraft_types) for _ in range(num_segments)])
        self.distance_list = self._duplicate_with_reversal([random.uniform(100, 6000) for _ in range(num_segments)])        
        self.cruise_atitude_list = self._duplicate_with_reversal([random.randint(100, 300) * 100 for _ in range(num_segments)])
        self.method_list = [random.choice(['V2_2.16', 'V2_1_5']) for _ in range(2*num_segments)]

        self._make_dataframe()

    def _duplicate_with_reversal(self, input_list):
        input_list = input_list + list(reversed(input_list))
        return input_list

    def _make_dataframe(self):
        # atmosfair_data_columns = ['departure', 'arrival', 'pax', 'travelClass', 'flightNumber', 'flightDate','aircraft', 'charter', 
        # 'UniqueID atmosfair', 'Unnamed: 11', 'flight', 'specific fuel consumption', 'share of fuel use in cruise', 'fuel use', 	
        # 'fuel use in critical altitudes', 'CO2', 'CO2RFI2', 'CO2RFI2.7', 'CO2RFI4', 'CO2DEFRA', 'CO2GHGGRI', 'CO2ICAO', 'CO2VFU',
        # 'aircraft.1', 'distance','cruise altitude', 'method']
        indices = list(range(len(self.associated_flight.to_flight_numbers) + len(self.associated_flight.return_flight_numbers)))
        current_row = 0
        self.atmosfair_df = pd.DataFrame(columns=atmosfair_data_columns, index=indices)
        for i in range(len(self.associated_flight.all_segment_endpoint_tuples)):
            row_df = [self.associated_flight.all_segment_endpoint_tuples[i][0], self.associated_flight.all_segment_endpoint_tuples[i][1], self.pax, 
                self.associated_flight.travel_class, self.associated_flight.all_flight_numbers[i], 
                self.associated_flight.all_flight_dates[i].strftime("%d.%m.%Y"), self.aircraft, self.charter, self.uniqueID, self.unnamed, 
                self.flight_column, self.specific_fuel_consumption_list[i], self.share_of_fuel_use_in_cruise_list[i], self.fuel_use_list[i], 
                self.fuel_use_in_critical_alt_list[i], self.CO2_list[i], self.CO2RFI2_list[i], self.CO2RFI27_list[i], self.CO2RFI4_list[i],
                self.CO2DEFRA_list[i], self.CO2GHGGRI_list[i], self.CO2ICAO_list[i], self.CO2VFU_list[i], self.aircraft1_list[i], 
                self.distance_list[i], self.cruise_atitude_list[i], self.method_list[i]]
            self.atmosfair_df.loc[current_row] = row_df
            current_row += 1

    def get_dataframe(self):
        return self.atmosfair_df

# To write to the test files, we must do the following steps
# 1. Make copies of the base test files, place them in the outer folder
# 2. Append data to the files from the pandas dataframes that have been made here.

# There's 4 HR files to write, 2017, 2018, 2019, 2020, all with the same format
# There's 3 Flight files to write, Spesen, Airplus (same columns) and BTA (different columns)
# There's 1 Atmosfair CSV to write, entirely anew.
# Initial run should generate data into the hr_bta_matches file, which can then be updated manually and run afterwards nicely.  

def write_excel_file(df, file_path):
    book = load_workbook(file_path)
    writer = pd.ExcelWriter(file_path, engine='openpyxl')
    writer.book = book
    
    writer.sheets = dict((ws.title, ws) for ws in book.worksheets)
    df.to_excel(writer, index= False)
    writer.save()

def write_csv_file(df, file_path):
    df.to_csv(file_path, index=False)

def create_and_write_to_file(config, hr_data, flight_data, atmos_data):
    base_file_folder = 'test-base-files'
    target_file_folder = 'data-tests'

    # Clean all previous generated files in data-tests folder except the templates 
    # for file in os.listdir(target_file_folder):
    
        # if os.path.isfile(file_path):
        #     os.remove(file_path)
        # elif os.path.isdir(os.path.join(target_file_folder, file)):
        #     pass
    if os.path.exists(target_file_folder) and os.path.isdir(target_file_folder):
        shutil.rmtree(target_file_folder)
    os.mkdir(target_file_folder)

    print('Cleared data-tests directory!')
    # Copy all files in template folder to the outside first
    shutil.copytree(base_file_folder, target_file_folder, dirs_exist_ok=True)
    write_excel_file(flight_data[0], os.path.join(target_file_folder, config['spesen_legs_filename']))
    write_excel_file(flight_data[1], os.path.join(target_file_folder, config['airplus_legs_filename']))
    write_excel_file(flight_data[2], os.path.join(target_file_folder, config['bta_legs_filename']))
    write_excel_file(hr_data[0], os.path.join(target_file_folder, config['hr_before_2019_filename']))
    write_excel_file(hr_data[1], os.path.join(target_file_folder, config['hr_since_2019_filename']))
    write_csv_file(atmos_data, os.path.join(target_file_folder, 'atmosfair_responses', config['atmosfair_filename']))

    print('Written data to file!')

def generate_mock_data(config=None):
    print('-----------------')
    print('Starting Mock Data Generation utility')
    print('------------------')

    if config is None:
        config = get_default_mock_config()
        print('Using default mock config')

    list_non_flying_employees = []
    list_flying_employees = []
    list_flying_guests = []
    list_flying_employees_not_in_hr = []

    for i in range(config['num_non_flying_employees']):
        list_non_flying_employees.append(Employee(fake))
    
    # Generating people and employees
    if config['people_distribution'] == 'manual':
        # All values of splits are manually mentioned in this case
        for i in range(config['num_flying_employees']):
            list_flying_employees.append(Employee(fake))
        for i in range(config['num_flying_guests']):
            list_flying_guests.append(Person(fake))
        for i in range(config['num_flying_employees_not_in_hr']):
            list_flying_employees_not_in_hr.append(Person(fake))
    else:
        for _ in range(config['num_all_flying_people']):
            flying_person_type = random.choice(['employee', 'guest', 'unregistered_employee'])
            if flying_person_type == 'employee':
                list_flying_employees.append(Employee(fake))
            elif flying_person_type == 'guest':
                list_flying_guests.append(Person(fake))
            elif flying_person_type == 'unregistered_employee':
                list_flying_employees_not_in_hr.append(Person(fake))
        
    list_all_flying_people = list_flying_employees + list_flying_guests + list_flying_employees_not_in_hr
    print('Created', len(list_all_flying_people) + len(list_non_flying_employees), 'people!')
    print(len(list_all_flying_people), 'people have taken flights in the past period.')

    # Every flying person needs to go to a flight booking.
    # We do this through shuffling the list and then iterating through it - no duplicates ensue.
    # Number of total flying people = number of total flights (round-trips)
    actual_passenger_list = copy.deepcopy(list_all_flying_people)
    random.shuffle(actual_passenger_list)
    all_flights = []
    spesen_flights = []
    airplus_flights = []
    bta_flights = []
    
    if config['flight_distribution'] == 'manual':
        # Passenger list is already shuffled. Requirement is set that more passengers are generated than flights needed.
        # With this constraint, we start with index 0 sequentially and assign the passengers to the required flight data.
        current_passenger_index = 0
        for _ in range(config['num_flights_in_spesen']):
            new_flight = Flight_Spesen_Airplus_Data(fake, actual_passenger_list[current_passenger_index], 'spesen')
            spesen_flights.append(new_flight)
            all_flights.append(new_flight)
            current_passenger_index += 1
        for _ in range(config['num_flights_in_airplus']):
            new_flight = Flight_Spesen_Airplus_Data(fake, actual_passenger_list[current_passenger_index], 'airplus')
            airplus_flights.append(new_flight)
            all_flights.append(new_flight)
            current_passenger_index += 1
        for _ in range(config['num_flights_in_bta']):
            new_flight = Flight_BTA_Data(fake, actual_passenger_list[current_passenger_index])
            bta_flights.append(new_flight)
            all_flights.append(new_flight)
            current_passenger_index += 1
    else:
        for passenger in actual_passenger_list:
            flight_type = random.choice(['bta', 'spesen', 'airplus'])
            # flight_type = random.choice(['spesen', 'airplus'])
            # flight_type = random.choice(['bta'])
            if flight_type == 'bta':
                new_flight = Flight_BTA_Data(fake, passenger)
                bta_flights.append(new_flight)
                all_flights.append(new_flight)
            elif flight_type == 'spesen':
                new_flight = Flight_Spesen_Airplus_Data(fake, passenger, 'spesen')
                spesen_flights.append(new_flight)
                all_flights.append(new_flight)
            elif flight_type == 'airplus':
                new_flight = Flight_Spesen_Airplus_Data(fake, passenger, 'airplus')
                airplus_flights.append(new_flight)
                all_flights.append(new_flight)

    print('----------')
    print('Created', len(all_flights), 'round trips!')
    print('with', sum([2* x.number_of_segments for x in spesen_flights]), 'segments in the spesen records. (' + str(len(spesen_flights))+ ') trips.')
    print('with', sum([2* x.number_of_segments for x in airplus_flights]), 'segments in the airplus records. ('+ str(len(airplus_flights))+') trips.')
    print('with', sum([2* x.number_of_segments for x in bta_flights]), 'segments in the bta records. ('+str(len(bta_flights))+ ') trips.')

    # Control the proportion of flights that will have data in atmosfair reponse previously, and populate the CSV as needed.
    proportion_of_precached_atmosfair_data = 0.7
    num_flights_with_atmosfair_data = math.floor(len(all_flights) * proportion_of_precached_atmosfair_data)
    random.shuffle(all_flights)
    flights_with_atmosfair_data = all_flights[:num_flights_with_atmosfair_data]
    existing_atmosfair_data = []

    # Initialize Atmosfair data for all these flights
    for flight in flights_with_atmosfair_data:
        existing_atmosfair_data.append(AtmosfairFlightData(flight, fake))
    print('----------')
    print('Created atmosfair data for', len(existing_atmosfair_data), 'trips.')
    print('----------')

    # Begin writing all data to files.
    # HR Data
    hr_dataframe_before_2019 = pd.concat(person.get_dataframe('before-2019') for person in list_flying_employees).reset_index(drop=True)
    hr_dataframe_since_2019 = pd.concat(person.get_dataframe('since-2019') for person in list_flying_employees).reset_index(drop=True)
    
    # Flight Data
    if len(spesen_flights) > 0:
        spesen_flight_dataframe = pd.concat(flight.get_dataframe() for flight in spesen_flights).reset_index(drop=True)
    if len(airplus_flights) > 0:
        airplus_flight_dataframe = pd.concat(flight.get_dataframe() for flight in airplus_flights).reset_index(drop=True)
    if len(bta_flights) > 0:
        bta_flight_dataframe = pd.concat(flight.get_dataframe() for flight in bta_flights).reset_index(drop=True)
    
    # Atmosfair Data
    if len(existing_atmosfair_data) > 0:
        atmosfair_flight_dataframe = pd.concat(atmosfair_data.get_dataframe() for atmosfair_data in existing_atmosfair_data).reset_index(drop=True)
    # print(atmosfair_flight_dataframe)

    hr_data = (hr_dataframe_before_2019, hr_dataframe_since_2019)
    flight_data = (spesen_flight_dataframe, airplus_flight_dataframe, bta_flight_dataframe)
    
    create_and_write_to_file(config, hr_data, flight_data, atmosfair_flight_dataframe)


def get_default_mock_config():
    default_mock_config = {}
    default_mock_config['num_people_overall'] = 50
    default_mock_config['num_non_flying_employees'] = 30  # First value considered
    default_mock_config['proportion_of_flying_population'] = 0.6 # This is considered if the above number is not mentioned.

    default_mock_config['num_all_flying_people'] = default_mock_config['num_people_overall'] - \
            default_mock_config['num_non_flying_employees'] ## In default, it's 20

    default_mock_config['people_distribution'] = 'manual' ## other option is 'random', randomly choosing what kind the flying people are.
    default_mock_config['num_flying_employees'] = 14
    default_mock_config['num_flying_guests'] = 3
    default_mock_config['num_flying_employees_not_in_hr'] = 3


    default_mock_config['flight_distribution'] = 'manual' ## other option is 'random'
    default_mock_config['num_flights_in_spesen'] = 10
    default_mock_config['num_flights_in_airplus'] = 4
    default_mock_config['num_flights_in_bta'] = 6 # Sum should be less than or equal to the number of flying people 

    default_mock_config['hr_before_2019_filename'] = 'hr-before-2019-base.xlsx'
    default_mock_config['hr_since_2019_filename'] = 'hr-since-2019-base.xlsx'
    default_mock_config['spesen_legs_filename'] = 'spesen-legs-base.xlsx'
    default_mock_config['airplus_legs_filename'] = 'airplus-legs-base.xlsx'
    default_mock_config['bta_legs_filename'] = 'bta-legs-base.xlsx'
    default_mock_config['atmosfair_filename'] = 'atmosfair-base.csv'

    return default_mock_config

generate_mock_data()
