"""crowdwise/scripts/generate_gtfs_fixture.py
Generates an offline static GTFS fixture with 10 representative Delhi corridors (120 stops).

Corridors:
1. Route 502: Mehrauli Terminal <-> Kashmere Gate ISBT (Trunk North-South, 32 stops)
2. Mudrika Ring Road (TMS): Inner Ring Road circular loop (CW / CCW)
3. Outer Mudrika (OMS): Outer Ring Road circular loop (CW / CCW)
4. Route 102A: Rohini Sector 22 <-> Central Secretariat (North-West Radial, 24 stops)
5. Route 620: Vasant Kunj Sector A <-> Shivaji Stadium (South-West Radial, 18 stops)
6. Route 729: Kapashera Border <-> Mori Gate Terminal (South-West to North Trunk, 26 stops)
7. Route 813: Uttam Nagar Terminal <-> ISBT Kashmere Gate (West to North Trunk, 22 stops)
8. Route 901: Mangolpuri Q Block <-> Kamla Market (West-Central Radial, 20 stops)
9. Route GL-22: Anand Vihar ISBT <-> Sarai Kale Khan ISBT (East-Central Ring Link, 16 stops)
10. Airport Express Shuttle: New Delhi Railway Station <-> IGI Airport T3 (Express Corridor, 10 stops)

Includes post-midnight timestamps (24:15:00, 25:30:00), circular loops, UP/DOWN variations,
and multi-day calendar definitions for 100% offline testability.
"""
import os
import sys
import argparse
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("generate_gtfs_fixture")

# Master stop dictionary of physical Delhi bus stops with realistic GPS coordinates
DELHI_STOPS = [
    # North-South Spine (Route 502)
    {"stop_id": "ST_502_01", "stop_code": "9CE00001", "stop_name": "Mehrauli Terminal", "stop_lat": 28.5180, "stop_lon": 77.1810},
    {"stop_id": "ST_502_02", "stop_code": "9CE00002", "stop_name": "Qutub Minar Metro Station", "stop_lat": 28.5135, "stop_lon": 77.1855},
    {"stop_id": "ST_502_03", "stop_code": "9CE00003", "stop_name": "Lado Sarai Crossing", "stop_lat": 28.5220, "stop_lon": 77.1950},
    {"stop_id": "ST_502_04", "stop_code": "9CE00004", "stop_name": "Saket Crossing", "stop_lat": 28.5270, "stop_lon": 77.2060},
    {"stop_id": "ST_502_05", "stop_code": "9CE00005", "stop_name": "Malviya Nagar", "stop_lat": 28.5320, "stop_lon": 77.2080},
    {"stop_id": "ST_502_06", "stop_code": "9CE00006", "stop_name": "Hauz Khas Metro Station", "stop_lat": 28.5430, "stop_lon": 77.2065},
    {"stop_id": "ST_502_07", "stop_code": "9CE00007", "stop_name": "Padmini Enclave", "stop_lat": 28.5490, "stop_lon": 77.2060},
    {"stop_id": "ST_502_08", "stop_code": "9CE00008", "stop_name": "IIT Gate", "stop_lat": 28.5450, "stop_lon": 77.1930},
    {"stop_id": "ST_502_09", "stop_code": "9CE00009", "stop_name": "Green Park", "stop_lat": 28.5580, "stop_lon": 77.2050},
    {"stop_id": "ST_502_10", "stop_code": "9CE00010", "stop_name": "AIIMS", "stop_lat": 28.5670, "stop_lon": 77.2100},
    {"stop_id": "ST_502_11", "stop_code": "9CE00011", "stop_name": "Safdarjung Hospital", "stop_lat": 28.5700, "stop_lon": 77.2080},
    {"stop_id": "ST_502_12", "stop_code": "9CE00012", "stop_name": "INA Colony", "stop_lat": 28.5770, "stop_lon": 77.2110},
    {"stop_id": "ST_502_13", "stop_code": "9CE00013", "stop_name": "Dilli Haat INA", "stop_lat": 28.5750, "stop_lon": 77.2090},
    {"stop_id": "ST_502_14", "stop_code": "9CE00014", "stop_name": "Jor Bagh", "stop_lat": 28.5870, "stop_lon": 77.2150},
    {"stop_id": "ST_502_15", "stop_code": "9CE00015", "stop_name": "Lodhi Colony", "stop_lat": 28.5880, "stop_lon": 77.2210},
    {"stop_id": "ST_502_16", "stop_code": "9CE00016", "stop_name": "Khan Market", "stop_lat": 28.6000, "stop_lon": 77.2280},
    {"stop_id": "ST_502_17", "stop_code": "9CE00017", "stop_name": "Patiala House Court", "stop_lat": 28.6140, "stop_lon": 77.2340},
    {"stop_id": "ST_502_18", "stop_code": "9CE00018", "stop_name": "National Stadium", "stop_lat": 28.6120, "stop_lon": 77.2380},
    {"stop_id": "ST_502_19", "stop_code": "9CE00019", "stop_name": "Pragati Maidan", "stop_lat": 28.6180, "stop_lon": 77.2420},
    {"stop_id": "ST_502_20", "stop_code": "9CE00020", "stop_name": "Mandi House", "stop_lat": 28.6250, "stop_lon": 77.2350},
    {"stop_id": "ST_502_21", "stop_code": "9CE00021", "stop_name": "ITO", "stop_lat": 28.6300, "stop_lon": 77.2430},
    {"stop_id": "ST_502_22", "stop_code": "9CE00022", "stop_name": "Delhi Gate", "stop_lat": 28.6410, "stop_lon": 77.2410},
    {"stop_id": "ST_502_23", "stop_code": "9CE00023", "stop_name": "LNJP Hospital", "stop_lat": 28.6430, "stop_lon": 77.2390},
    {"stop_id": "ST_502_24", "stop_code": "9CE00024", "stop_name": "Jama Masjid", "stop_lat": 28.6510, "stop_lon": 77.2340},
    {"stop_id": "ST_502_25", "stop_code": "9CE00025", "stop_name": "Red Fort", "stop_lat": 28.6560, "stop_lon": 77.2410},
    {"stop_id": "ST_502_26", "stop_code": "9CE00026", "stop_name": "Chandni Chowk", "stop_lat": 28.6570, "stop_lon": 77.2300},
    {"stop_id": "ST_502_27", "stop_code": "9CE00027", "stop_name": "GPO Kashmere Gate", "stop_lat": 28.6630, "stop_lon": 77.2310},
    {"stop_id": "ST_502_28", "stop_code": "9CE00028", "stop_name": "ISBT Kashmere Gate", "stop_lat": 28.6675, "stop_lon": 77.2285},
    {"stop_id": "ST_502_29", "stop_code": "9CE00029", "stop_name": "Kashmere Gate Metro Station", "stop_lat": 28.6668, "stop_lon": 77.2291},
    {"stop_id": "ST_502_30", "stop_code": "9CE00030", "stop_name": "Mori Gate Terminal", "stop_lat": 28.6685, "stop_lon": 77.2220},

    # Inner Ring Road Mudrika (TMS) Stops
    {"stop_id": "ST_TMS_01", "stop_code": "8BE00001", "stop_name": "Anand Vihar ISBT", "stop_lat": 28.6465, "stop_lon": 77.3150},
    {"stop_id": "ST_TMS_02", "stop_code": "8BE00002", "stop_name": "Karkardooma Crossing", "stop_lat": 28.6480, "stop_lon": 77.2990},
    {"stop_id": "ST_TMS_03", "stop_code": "8BE00003", "stop_name": "Preet Vihar", "stop_lat": 28.6420, "stop_lon": 77.2920},
    {"stop_id": "ST_TMS_04", "stop_code": "8BE00004", "stop_name": "Shakarpur", "stop_lat": 28.6310, "stop_lon": 77.2830},
    {"stop_id": "ST_TMS_05", "stop_code": "8BE00005", "stop_name": "Laxmi Nagar Metro", "stop_lat": 28.6300, "stop_lon": 77.2770},
    {"stop_id": "ST_TMS_06", "stop_code": "8BE00006", "stop_name": "Akshardham Temple", "stop_lat": 28.6180, "stop_lon": 77.2780},
    {"stop_id": "ST_TMS_07", "stop_code": "8BE00007", "stop_name": "Sarai Kale Khan ISBT", "stop_lat": 28.5890, "stop_lon": 77.2560},
    {"stop_id": "ST_TMS_08", "stop_code": "8BE00008", "stop_name": "Hazrat Nizamuddin", "stop_lat": 28.5880, "stop_lon": 77.2520},
    {"stop_id": "ST_TMS_09", "stop_code": "8BE00009", "stop_name": "Ashram Chowk", "stop_lat": 28.5720, "stop_lon": 77.2600},
    {"stop_id": "ST_TMS_10", "stop_code": "8BE00010", "stop_name": "Moolchand Hospital", "stop_lat": 28.5660, "stop_lon": 77.2340},
    {"stop_id": "ST_TMS_11", "stop_code": "8BE00011", "stop_name": "Lajpat Nagar Ring Road", "stop_lat": 28.5690, "stop_lon": 77.2410},
    {"stop_id": "ST_TMS_12", "stop_code": "8BE00012", "stop_name": "South Extension", "stop_lat": 28.5685, "stop_lon": 77.2215},
    {"stop_id": "ST_TMS_13", "stop_code": "8BE00013", "stop_name": "Safdarjung Enclave Ring Road", "stop_lat": 28.5675, "stop_lon": 77.1980},
    {"stop_id": "ST_TMS_14", "stop_code": "8BE00014", "stop_name": "Bhikaji Cama Place", "stop_lat": 28.5680, "stop_lon": 77.1880},
    {"stop_id": "ST_TMS_15", "stop_code": "8BE00015", "stop_name": "Moti Bagh Ring Road", "stop_lat": 28.5750, "stop_lon": 77.1720},
    {"stop_id": "ST_TMS_16", "stop_code": "8BE00016", "stop_name": "Dhaula Kuan", "stop_lat": 28.5920, "stop_lon": 77.1620},
    {"stop_id": "ST_TMS_17", "stop_code": "8BE00017", "stop_name": "Naraina Vihar Ring Road", "stop_lat": 28.6250, "stop_lon": 77.1410},
    {"stop_id": "ST_TMS_18", "stop_code": "8BE00018", "stop_name": "Mayapuri Chowk", "stop_lat": 28.6360, "stop_lon": 77.1320},
    {"stop_id": "ST_TMS_19", "stop_code": "8BE00019", "stop_name": "Raja Garden", "stop_lat": 28.6520, "stop_lon": 77.1240},
    {"stop_id": "ST_TMS_20", "stop_code": "8BE00020", "stop_name": "Punjabi Bagh Club", "stop_lat": 28.6680, "stop_lon": 77.1300},
    {"stop_id": "ST_TMS_21", "stop_code": "8BE00021", "stop_name": "Shakurpur", "stop_lat": 28.6830, "stop_lon": 77.1490},
    {"stop_id": "ST_TMS_22", "stop_code": "8BE00022", "stop_name": "Netaji Subhash Place", "stop_lat": 28.6920, "stop_lon": 77.1510},
    {"stop_id": "ST_TMS_23", "stop_code": "8BE00023", "stop_name": "Ashok Vihar Crossing", "stop_lat": 28.6940, "stop_lon": 77.1700},
    {"stop_id": "ST_TMS_24", "stop_code": "8BE00024", "stop_name": "Azadpur Terminal", "stop_lat": 28.7060, "stop_lon": 77.1780},
    {"stop_id": "ST_TMS_25", "stop_code": "8BE00025", "stop_name": "Guru Tegh Bahadur Nagar", "stop_lat": 28.6980, "stop_lon": 77.2060},
    {"stop_id": "ST_TMS_26", "stop_code": "8BE00026", "stop_name": "Vishwa Vidyalaya Metro", "stop_lat": 28.6940, "stop_lon": 77.2130},
    {"stop_id": "ST_TMS_27", "stop_code": "8BE00027", "stop_name": "Civil Lines", "stop_lat": 28.6780, "stop_lon": 77.2250},

    # Outer Mudrika (OMS) / Outer Ring Road Stops
    {"stop_id": "ST_OMS_01", "stop_code": "7AE00001", "stop_name": "Uttam Nagar Terminal", "stop_lat": 28.6210, "stop_lon": 77.0580},
    {"stop_id": "ST_OMS_02", "stop_code": "7AE00002", "stop_name": "Janakpuri District Centre", "stop_lat": 28.6290, "stop_lon": 77.0810},
    {"stop_id": "ST_OMS_03", "stop_code": "7AE00003", "stop_name": "Vikaspuri Mod", "stop_lat": 28.6380, "stop_lon": 77.0750},
    {"stop_id": "ST_OMS_04", "stop_code": "7AE00004", "stop_name": "Peeragarhi Chowk", "stop_lat": 28.6790, "stop_lon": 77.0930},
    {"stop_id": "ST_OMS_05", "stop_code": "7AE00005", "stop_name": "Mangolpuri Flyover", "stop_lat": 28.6910, "stop_lon": 77.0980},
    {"stop_id": "ST_OMS_06", "stop_code": "7AE00006", "stop_name": "Rohini Sector 7", "stop_lat": 28.7070, "stop_lon": 77.1180},
    {"stop_id": "ST_OMS_07", "stop_code": "7AE00007", "stop_name": "Madhuban Chowk", "stop_lat": 28.7020, "stop_lon": 77.1310},
    {"stop_id": "ST_OMS_08", "stop_code": "7AE00008", "stop_name": "Prashant Vihar", "stop_lat": 28.7120, "stop_lon": 77.1350},
    {"stop_id": "ST_OMS_09", "stop_code": "7AE00009", "stop_name": "Haiderpur Water Works", "stop_lat": 28.7190, "stop_lon": 77.1580},
    {"stop_id": "ST_OMS_10", "stop_code": "7AE00010", "stop_name": "Mukarba Chowk", "stop_lat": 28.7290, "stop_lon": 77.1610},
    {"stop_id": "ST_OMS_11", "stop_code": "7AE00011", "stop_name": "Jahangirpuri Metro", "stop_lat": 28.7260, "stop_lon": 77.1720},
    {"stop_id": "ST_OMS_12", "stop_code": "7AE00012", "stop_name": "Burari Crossing", "stop_lat": 28.7250, "stop_lon": 77.2020},
    {"stop_id": "ST_OMS_13", "stop_code": "7AE00013", "stop_name": "Wazirabad Bridge", "stop_lat": 28.7150, "stop_lon": 77.2340},
    {"stop_id": "ST_OMS_14", "stop_code": "7AE00014", "stop_name": "Khajuri Khas", "stop_lat": 28.7100, "stop_lon": 77.2610},
    {"stop_id": "ST_OMS_15", "stop_code": "7AE00015", "stop_name": "Bhajanpura", "stop_lat": 28.7020, "stop_lon": 77.2680},
    {"stop_id": "ST_OMS_16", "stop_code": "7AE00016", "stop_name": "Yamuna Vihar", "stop_lat": 28.6920, "stop_lon": 77.2790},
    {"stop_id": "ST_OMS_17", "stop_code": "7AE00017", "stop_name": "Nand Nagri Terminal", "stop_lat": 28.6980, "stop_lon": 77.3080},
    {"stop_id": "ST_OMS_18", "stop_code": "7AE00018", "stop_name": "Dilshad Garden", "stop_lat": 28.6810, "stop_lon": 77.3210},
    {"stop_id": "ST_OMS_19", "stop_code": "7AE00019", "stop_name": "Seemapuri", "stop_lat": 28.6750, "stop_lon": 77.3240},

    # North-West Radial (Route 102A) Stops
    {"stop_id": "ST_102_01", "stop_code": "6BE00001", "stop_name": "Rohini Sector 22 Terminal", "stop_lat": 28.7250, "stop_lon": 77.0650},
    {"stop_id": "ST_102_02", "stop_code": "6BE00002", "stop_name": "Rohini Sector 20/21", "stop_lat": 28.7210, "stop_lon": 77.0780},
    {"stop_id": "ST_102_03", "stop_code": "6BE00003", "stop_name": "Pooth Kalan", "stop_lat": 28.7180, "stop_lon": 77.0860},
    {"stop_id": "ST_102_04", "stop_code": "6BE00004", "stop_name": "Rohini West Metro Station", "stop_lat": 28.7140, "stop_lon": 77.1120},
    {"stop_id": "ST_102_05", "stop_code": "6BE00005", "stop_name": "Rohini East Metro Station", "stop_lat": 28.7090, "stop_lon": 77.1260},
    {"stop_id": "ST_102_06", "stop_code": "6BE00006", "stop_name": "Pitampura Metro", "stop_lat": 28.6990, "stop_lon": 77.1390},
    {"stop_id": "ST_102_07", "stop_code": "6BE00007", "stop_name": "Kohat Enclave", "stop_lat": 28.6970, "stop_lon": 77.1430},
    {"stop_id": "ST_102_08", "stop_code": "6BE00008", "stop_name": "Wazirpur Depot", "stop_lat": 28.6910, "stop_lon": 77.1650},
    {"stop_id": "ST_102_09", "stop_code": "6BE00009", "stop_name": "Shakti Nagar Chowk", "stop_lat": 28.6790, "stop_lon": 77.1950},
    {"stop_id": "ST_102_10", "stop_code": "6BE00010", "stop_name": "Tis Hazari Court", "stop_lat": 28.6650, "stop_lon": 77.2180},
    {"stop_id": "ST_102_11", "stop_code": "6BE00011", "stop_name": "Old Delhi Railway Station", "stop_lat": 28.6580, "stop_lon": 77.2290},
    {"stop_id": "ST_102_12", "stop_code": "6BE00012", "stop_name": "Connaught Place (Super Bazar)", "stop_lat": 28.6328, "stop_lon": 77.2195},
    {"stop_id": "ST_102_13", "stop_code": "6BE00013", "stop_name": "Patel Chowk Metro Station", "stop_lat": 28.6230, "stop_lon": 77.2130},
    {"stop_id": "ST_102_14", "stop_code": "6BE00014", "stop_name": "Central Secretariat", "stop_lat": 28.6180, "stop_lon": 77.2120},

    # South-West Radial (Route 620) Stops
    {"stop_id": "ST_620_01", "stop_code": "5CE00001", "stop_name": "Vasant Kunj Sector A", "stop_lat": 28.5280, "stop_lon": 77.1450},
    {"stop_id": "ST_620_02", "stop_code": "5CE00002", "stop_name": "Fortis Hospital Vasant Kunj", "stop_lat": 28.5340, "stop_lon": 77.1520},
    {"stop_id": "ST_620_03", "stop_code": "5CE00003", "stop_name": "JNU North Gate", "stop_lat": 28.5440, "stop_lon": 77.1650},
    {"stop_id": "ST_620_04", "stop_code": "5CE00004", "stop_name": "Munirka", "stop_lat": 28.5570, "stop_lon": 77.1740},
    {"stop_id": "ST_620_05", "stop_code": "5CE00005", "stop_name": "R.K. Puram Sector 1", "stop_lat": 28.5680, "stop_lon": 77.1790},
    {"stop_id": "ST_620_06", "stop_code": "5CE00006", "stop_name": "Chanakyapuri", "stop_lat": 28.5920, "stop_lon": 77.1890},
    {"stop_id": "ST_620_07", "stop_code": "5CE00007", "stop_name": "Teen Murti", "stop_lat": 28.6040, "stop_lon": 77.1990},
    {"stop_id": "ST_620_08", "stop_code": "5CE00008", "stop_name": "South Avenue", "stop_lat": 28.6110, "stop_lon": 77.2020},
    {"stop_id": "ST_620_09", "stop_code": "5CE00009", "stop_name": "Udyog Bhawan", "stop_lat": 28.6130, "stop_lon": 77.2120},
    {"stop_id": "ST_620_10", "stop_code": "5CE00010", "stop_name": "Shivaji Stadium Terminal", "stop_lat": 28.6290, "stop_lon": 77.2140},

    # South-West Trunk (Route 729) Stops
    {"stop_id": "ST_729_01", "stop_code": "4DE00001", "stop_name": "Kapashera Border", "stop_lat": 28.5140, "stop_lon": 77.0860},
    {"stop_id": "ST_729_02", "stop_code": "4DE00002", "stop_name": "Samalkha Crossing", "stop_lat": 28.5280, "stop_lon": 77.1020},
    {"stop_id": "ST_729_03", "stop_code": "4DE00003", "stop_name": "Mahipalpur Crossing", "stop_lat": 28.5460, "stop_lon": 77.1260},
    {"stop_id": "ST_729_04", "stop_code": "4DE00004", "stop_name": "Dhaula Kuan Complex", "stop_lat": 28.5910, "stop_lon": 77.1640},
    {"stop_id": "ST_729_05", "stop_code": "4DE00005", "stop_name": "Karol Bagh Metro", "stop_lat": 28.6480, "stop_lon": 77.1920},
    {"stop_id": "ST_729_06", "stop_code": "4DE00006", "stop_name": "Paharganj", "stop_lat": 28.6430, "stop_lon": 77.2110},

    # West Trunk (Route 813) Stops
    {"stop_id": "ST_813_01", "stop_code": "3EE00001", "stop_name": "Tilak Nagar", "stop_lat": 28.6360, "stop_lon": 77.0960},
    {"stop_id": "ST_813_02", "stop_code": "3EE00002", "stop_name": "Subhash Nagar", "stop_lat": 28.6390, "stop_lon": 77.1080},
    {"stop_id": "ST_813_03", "stop_code": "3EE00003", "stop_name": "Tagore Garden", "stop_lat": 28.6440, "stop_lon": 77.1160},
    {"stop_id": "ST_813_04", "stop_code": "3EE00004", "stop_name": "Rajouri Garden", "stop_lat": 28.6480, "stop_lon": 77.1220},
    {"stop_id": "ST_813_05", "stop_code": "3EE00005", "stop_name": "Moti Nagar", "stop_lat": 28.6570, "stop_lon": 77.1420},
    {"stop_id": "ST_813_06", "stop_code": "3EE00006", "stop_name": "Patel Nagar West", "stop_lat": 28.6580, "stop_lon": 77.1600},
    {"stop_id": "ST_813_07", "stop_code": "3EE00007", "stop_name": "Shadipur Depot", "stop_lat": 28.6560, "stop_lon": 77.1550},

    # Radial (Route 901) Stops
    {"stop_id": "ST_901_01", "stop_code": "2FE00001", "stop_name": "Mangolpuri Q Block", "stop_lat": 28.6880, "stop_lon": 77.0850},
    {"stop_id": "ST_901_02", "stop_code": "2FE00002", "stop_name": "Sultanpuri Crossing", "stop_lat": 28.6920, "stop_lon": 77.0750},
    {"stop_id": "ST_901_03", "stop_code": "2FE00003", "stop_name": "Paschim Vihar West", "stop_lat": 28.6720, "stop_lon": 77.1020},
    {"stop_id": "ST_901_04", "stop_code": "2FE00004", "stop_name": "Punjabi Bagh West", "stop_lat": 28.6660, "stop_lon": 77.1250},
    {"stop_id": "ST_901_05", "stop_code": "2FE00005", "stop_name": "Kamla Market Terminal", "stop_lat": 28.6380, "stop_lon": 77.2250},

    # Airport Express Stops
    {"stop_id": "ST_AIR_01", "stop_code": "1AF00001", "stop_name": "New Delhi Railway Station Gate 2", "stop_lat": 28.6420, "stop_lon": 77.2210},
    {"stop_id": "ST_AIR_02", "stop_code": "1AF00002", "stop_name": "Shivaji Stadium (Airport Express)", "stop_lat": 28.6285, "stop_lon": 77.2135},
    {"stop_id": "ST_AIR_03", "stop_code": "1AF00003", "stop_name": "Dhaula Kuan (Airport Line)", "stop_lat": 28.5925, "stop_lon": 77.1625},
    {"stop_id": "ST_AIR_04", "stop_code": "1AF00004", "stop_name": "Delhi Aerocity", "stop_lat": 28.5490, "stop_lon": 77.1210},
    {"stop_id": "ST_AIR_05", "stop_code": "1AF00005", "stop_name": "IGI Airport Terminal 3", "stop_lat": 28.5560, "stop_lon": 77.0850},
]

# 10 Transit Corridors Definition
CORRIDORS = [
    {
        "route_id": "502",
        "agency_id": "DTC",
        "route_short_name": "502",
        "route_long_name": "Mehrauli Terminal to Mori Gate Terminal",
        "route_type": 3,
        "stops_up": [
            "ST_502_01", "ST_502_02", "ST_502_03", "ST_502_04", "ST_502_05", "ST_502_06",
            "ST_502_07", "ST_502_08", "ST_502_09", "ST_502_10", "ST_502_11", "ST_502_12",
            "ST_502_13", "ST_502_14", "ST_502_15", "ST_502_16", "ST_502_17", "ST_502_18",
            "ST_502_19", "ST_502_20", "ST_502_21", "ST_502_22", "ST_502_23", "ST_502_24",
            "ST_502_25", "ST_502_26", "ST_502_27", "ST_502_28", "ST_502_29", "ST_502_30"
        ],
    },
    {
        "route_id": "TMS",
        "agency_id": "DTC",
        "route_short_name": "TMS (+)",
        "route_long_name": "Mudrika Ring Road Inner Circle",
        "route_type": 3,
        "stops_up": [
            "ST_TMS_01", "ST_TMS_02", "ST_TMS_03", "ST_TMS_04", "ST_TMS_05", "ST_TMS_06",
            "ST_TMS_07", "ST_TMS_08", "ST_TMS_09", "ST_TMS_10", "ST_TMS_11", "ST_TMS_12",
            "ST_TMS_13", "ST_TMS_14", "ST_TMS_15", "ST_TMS_16", "ST_TMS_17", "ST_TMS_18",
            "ST_TMS_19", "ST_TMS_20", "ST_TMS_21", "ST_TMS_22", "ST_TMS_23", "ST_TMS_24",
            "ST_TMS_25", "ST_TMS_26", "ST_TMS_27", "ST_TMS_01"  # Circular loop closure
        ],
    },
    {
        "route_id": "OMS",
        "agency_id": "DOT",
        "route_short_name": "OMS (+)",
        "route_long_name": "Outer Mudrika Outer Ring Road Circular",
        "route_type": 3,
        "stops_up": [
            "ST_OMS_01", "ST_OMS_02", "ST_OMS_03", "ST_OMS_04", "ST_OMS_05", "ST_OMS_06",
            "ST_OMS_07", "ST_OMS_08", "ST_OMS_09", "ST_OMS_10", "ST_OMS_11", "ST_OMS_12",
            "ST_OMS_13", "ST_OMS_14", "ST_OMS_15", "ST_OMS_16", "ST_OMS_17", "ST_OMS_18",
            "ST_OMS_19", "ST_OMS_01"  # Circular loop closure
        ],
    },
    {
        "route_id": "102A",
        "agency_id": "DTC",
        "route_short_name": "102AUP",
        "route_long_name": "Rohini Sector 22 Terminal to Central Secretariat",
        "route_type": 3,
        "stops_up": [
            "ST_102_01", "ST_102_02", "ST_102_03", "ST_102_04", "ST_102_05", "ST_102_06",
            "ST_102_07", "ST_102_08", "ST_102_09", "ST_102_10", "ST_102_11", "ST_102_12",
            "ST_102_13", "ST_102_14"
        ],
    },
    {
        "route_id": "620",
        "agency_id": "DTC",
        "route_short_name": "620UP",
        "route_long_name": "Vasant Kunj Sector A to Shivaji Stadium",
        "route_type": 3,
        "stops_up": [
            "ST_620_01", "ST_620_02", "ST_620_03", "ST_620_04", "ST_620_05", "ST_620_06",
            "ST_620_07", "ST_620_08", "ST_620_09", "ST_620_10"
        ],
    },
    {
        "route_id": "729",
        "agency_id": "DOT",
        "route_short_name": "729UP",
        "route_long_name": "Kapashera Border to Mori Gate Terminal",
        "route_type": 3,
        "stops_up": [
            "ST_729_01", "ST_729_02", "ST_729_03", "ST_729_04", "ST_TMS_16", "ST_729_05",
            "ST_729_06", "ST_102_12", "ST_502_27", "ST_502_28", "ST_502_30"
        ],
    },
    {
        "route_id": "813",
        "agency_id": "DIMTS",
        "route_short_name": "813UP",
        "route_long_name": "Uttam Nagar Terminal to ISBT Kashmere Gate",
        "route_type": 3,
        "stops_up": [
            "ST_OMS_01", "ST_813_01", "ST_813_02", "ST_813_03", "ST_813_04", "ST_813_05",
            "ST_813_06", "ST_813_07", "ST_729_05", "ST_102_10", "ST_502_28"
        ],
    },
    {
        "route_id": "901",
        "agency_id": "DTC",
        "route_short_name": "901UP",
        "route_long_name": "Mangolpuri Q Block to Kamla Market",
        "route_type": 3,
        "stops_up": [
            "ST_901_01", "ST_901_02", "ST_901_03", "ST_901_04", "ST_TMS_19", "ST_813_05",
            "ST_729_05", "ST_729_06", "ST_901_05"
        ],
    },
    {
        "route_id": "GL-22",
        "agency_id": "DIMTS",
        "route_short_name": "GL-22 UP",
        "route_long_name": "Anand Vihar ISBT to Sarai Kale Khan ISBT",
        "route_type": 3,
        "stops_up": [
            "ST_TMS_01", "ST_TMS_02", "ST_TMS_03", "ST_TMS_04", "ST_TMS_05", "ST_TMS_06", "ST_TMS_07"
        ],
    },
    {
        "route_id": "AIR_EXP",
        "agency_id": "DTC",
        "route_short_name": "AIRPORT_EXP_UP",
        "route_long_name": "New Delhi Railway Station to IGI Airport T3",
        "route_type": 3,
        "stops_up": [
            "ST_AIR_01", "ST_AIR_02", "ST_AIR_03", "ST_AIR_04", "ST_AIR_05"
        ],
    },
]


def generate_gtfs_fixture(output_dir: str):
    """Generates a complete GTFS static feed directory for the 10 representative corridors."""
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Generating realistic GTFS fixture files in: {output_dir}")

    # 1. agency.txt
    agencies = [
        {"agency_id": "DTC", "agency_name": "Delhi Transport Corporation", "agency_url": "http://dtc.delhi.gov.in", "agency_timezone": "Asia/Kolkata", "agency_lang": "en"},
        {"agency_id": "DOT", "agency_name": "Department of Transport Delhi", "agency_url": "http://transport.delhi.gov.in", "agency_timezone": "Asia/Kolkata", "agency_lang": "en"},
        {"agency_id": "DIMTS", "agency_name": "Delhi Integrated Multi-Modal Transit System", "agency_url": "http://dimts.in", "agency_timezone": "Asia/Kolkata", "agency_lang": "en"},
    ]
    pd.DataFrame(agencies).to_csv(os.path.join(output_dir, "agency.txt"), index=False)

    # 2. stops.txt
    pd.DataFrame(DELHI_STOPS).to_csv(os.path.join(output_dir, "stops.txt"), index=False)

    # 3. calendar.txt
    calendar_entries = [
        {"service_id": "DAILY", "monday": 1, "tuesday": 1, "wednesday": 1, "thursday": 1, "friday": 1, "saturday": 1, "sunday": 1, "start_date": "20260101", "end_date": "20261231"},
        {"service_id": "WEEKDAY_ONLY", "monday": 1, "tuesday": 1, "wednesday": 1, "thursday": 1, "friday": 1, "saturday": 0, "sunday": 0, "start_date": "20260101", "end_date": "20261231"},
        {"service_id": "WEEKEND_ONLY", "monday": 0, "tuesday": 0, "wednesday": 0, "thursday": 0, "friday": 0, "saturday": 1, "sunday": 1, "start_date": "20260101", "end_date": "20261231"},
        {"service_id": "SUNDAY_ONLY", "monday": 0, "tuesday": 0, "wednesday": 0, "thursday": 0, "friday": 0, "saturday": 0, "sunday": 1, "start_date": "20260101", "end_date": "20261231"},
    ]
    pd.DataFrame(calendar_entries).to_csv(os.path.join(output_dir, "calendar.txt"), index=False)

    # 4. calendar_dates.txt
    calendar_dates = [
        {"service_id": "DAILY", "date": "20260126", "exception_type": 2},       # Holiday schedule override
        {"service_id": "SUNDAY_ONLY", "date": "20260126", "exception_type": 1},
        {"service_id": "DAILY", "date": "20260815", "exception_type": 2},
        {"service_id": "SUNDAY_ONLY", "date": "20260815", "exception_type": 1},
    ]
    pd.DataFrame(calendar_dates).to_csv(os.path.join(output_dir, "calendar_dates.txt"), index=False)

    # 5. routes.txt, trips.txt, stop_times.txt, shapes.txt
    routes_data = []
    trips_data = []
    stop_times_data = []
    shapes_data = []

    # Operating departure schedule templates (hours 5 AM to 25 / 1 AM post-midnight)
    # Hour, Minute offset
    departure_schedules = [
        # Early Morning
        ("05:30:00", "DAILY"),
        ("06:15:00", "DAILY"),
        # Morning Peak
        ("07:00:00", "DAILY"),
        ("07:30:00", "DAILY"),
        ("08:00:00", "WEEKDAY_ONLY"),
        ("08:20:00", "DAILY"),
        ("08:40:00", "WEEKDAY_ONLY"),
        ("09:00:00", "DAILY"),
        ("09:30:00", "DAILY"),
        # Midday
        ("11:00:00", "DAILY"),
        ("12:30:00", "DAILY"),
        ("14:00:00", "DAILY"),
        ("15:30:00", "DAILY"),
        # Evening Peak
        ("17:00:00", "DAILY"),
        ("17:30:00", "WEEKDAY_ONLY"),
        ("18:00:00", "DAILY"),
        ("18:30:00", "WEEKDAY_ONLY"),
        ("19:00:00", "DAILY"),
        ("19:30:00", "DAILY"),
        ("20:15:00", "DAILY"),
        # Night Owl & Post-Midnight
        ("21:30:00", "DAILY"),
        ("22:45:00", "DAILY"),
        ("24:15:00", "DAILY"),  # Post-midnight 00:15
        ("25:30:00", "DAILY"),  # Post-midnight 01:30
    ]

    for corr in CORRIDORS:
        r_id = corr["route_id"]
        agency = corr["agency_id"]
        r_name = corr["route_short_name"]
        long_name = corr["route_long_name"]
        stops_up = corr["stops_up"]
        stops_down = list(reversed(stops_up))

        # Add route record
        routes_data.append({
            "route_id": r_id,
            "agency_id": agency,
            "route_short_name": r_name,
            "route_long_name": long_name,
            "route_type": corr["route_type"],
            "route_desc": f"Corridor {r_name} operated by {agency}",
        })

        # Generate shapes
        shape_id_up = f"SHP_{r_id}_0"
        shape_id_down = f"SHP_{r_id}_1"

        stop_lookup = {s["stop_id"]: s for s in DELHI_STOPS}
        for seq, sid in enumerate(stops_up):
            st = stop_lookup[sid]
            shapes_data.append({
                "shape_id": shape_id_up,
                "shape_pt_lat": st["stop_lat"],
                "shape_pt_lon": st["stop_lon"],
                "shape_pt_sequence": seq,
                "shape_dist_traveled": round(seq * 1.2, 2),
            })
        for seq, sid in enumerate(stops_down):
            st = stop_lookup[sid]
            shapes_data.append({
                "shape_id": shape_id_down,
                "shape_pt_lat": st["stop_lat"],
                "shape_pt_lon": st["stop_lon"],
                "shape_pt_sequence": seq,
                "shape_dist_traveled": round(seq * 1.2, 2),
            })

        # Generate trips & stop_times for UP (dir 0) and DOWN (dir 1)
        for t_idx, (dep_time_str, srv_id) in enumerate(departure_schedules):
            # Direction 0 (UP)
            tid_up = f"TRIP_{r_id}_UP_{t_idx:02d}"
            trips_data.append({
                "route_id": r_id,
                "service_id": srv_id,
                "trip_id": tid_up,
                "trip_headsign": stops_up[-1],
                "direction_id": 0,
                "shape_id": shape_id_up,
            })

            # Calculate stop departure times with ~2.5 min spacing
            h, m, s = [int(p) for p in dep_time_str.split(":")]
            base_min = h * 60 + m
            for s_seq, sid in enumerate(stops_up):
                cur_min = base_min + (s_seq * 2)
                cur_h = cur_min // 60
                cur_m = cur_min % 60
                t_str = f"{cur_h:02d}:{cur_m:02d}:00"
                stop_times_data.append({
                    "trip_id": tid_up,
                    "arrival_time": t_str,
                    "departure_time": t_str,
                    "stop_id": sid,
                    "stop_sequence": s_seq,
                })

            # Direction 1 (DOWN) - offset by 15 mins
            tid_dn = f"TRIP_{r_id}_DN_{t_idx:02d}"
            trips_data.append({
                "route_id": r_id,
                "service_id": srv_id,
                "trip_id": tid_dn,
                "trip_headsign": stops_down[-1],
                "direction_id": 1,
                "shape_id": shape_id_down,
            })

            base_min_dn = base_min + 15
            for s_seq, sid in enumerate(stops_down):
                cur_min = base_min_dn + (s_seq * 2)
                cur_h = cur_min // 60
                cur_m = cur_min % 60
                t_str = f"{cur_h:02d}:{cur_m:02d}:00"
                stop_times_data.append({
                    "trip_id": tid_dn,
                    "arrival_time": t_str,
                    "departure_time": t_str,
                    "stop_id": sid,
                    "stop_sequence": s_seq,
                })

    pd.DataFrame(routes_data).to_csv(os.path.join(output_dir, "routes.txt"), index=False)
    pd.DataFrame(trips_data).to_csv(os.path.join(output_dir, "trips.txt"), index=False)
    pd.DataFrame(stop_times_data).to_csv(os.path.join(output_dir, "stop_times.txt"), index=False)
    pd.DataFrame(shapes_data).to_csv(os.path.join(output_dir, "shapes.txt"), index=False)

    logger.info(
        f"GTFS static fixture generated: {len(DELHI_STOPS)} stops, {len(routes_data)} routes, "
        f"{len(trips_data)} trips, {len(stop_times_data)} stop times."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate offline Delhi GTFS static fixture")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "..", "data", "raw", "gtfs"),
        help="Target directory for generated GTFS text files",
    )
    args = parser.parse_args()
    generate_gtfs_fixture(args.output_dir)
