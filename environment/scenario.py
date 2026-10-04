"""
scenario.py
-----------
Builds the default disaster scenario on a real-world road network:
Old Dhaka (north bank) and Keraniganj (south bank) on either side of
the Buriganga River, linked by two bridges - Babubazar Bridge and
Postogola (1st Buriganga) Bridge.

  * Rescue vehicle starts at the Fire Service & Civil Defence HQ.
  * Hospital is Dhaka Medical College Hospital.
  * Some riverside roads are FLOODED and one road is BLOCKED, so the
    four search algorithms visibly behave differently and A* has a
    real reason to detour.

Coordinates are approximate positions of each landmark / intersection
(hand-placed, good to roughly a hundred metres) and road lengths are
estimated from straight-line distance. To use a different area, edit
NODES and ROADS below - nothing else in the project needs to change.
"""

from dataclasses import dataclass
from typing import List, Tuple

from environment.road_network import RoadNetwork, OPEN, FLOODED, BLOCKED
from environment.road_shapes import ROAD_SHAPES

NORTH = "north"
SOUTH = "south"

# id, name, lat, lon, area
NODES = [
    ("SHB", "Shahbagh",                         23.7380, 90.3959, NORTH),
    ("TSC", "Dhaka University (TSC)",           23.7325, 90.3960, NORTH),
    ("NLK", "Nilkhet",                          23.7330, 90.3858, NORTH),
    ("AZM", "Azimpur",                          23.7272, 90.3855, NORTH),
    ("PLS", "Palashi",                          23.7262, 90.3905, NORTH),
    ("DMC", "Dhaka Medical College Hospital",   23.7255, 90.3975, NORTH),
    ("CZH", "Curzon Hall",                      23.7268, 90.4012, NORTH),
    ("PRS", "National Press Club",              23.7305, 90.4055, NORTH),
    ("PLT", "Paltan",                           23.7345, 90.4115, NORTH),
    ("MTJ", "Motijheel",                        23.7325, 90.4185, NORTH),
    ("GLS", "Gulistan",                         23.7238, 90.4125, NORTH),
    ("FSH", "Fire Service HQ",                  23.7205, 90.4082, NORTH),
    ("BKB", "Bakshibazar",                      23.7225, 90.3920, NORTH),
    ("LLB", "Lalbagh Fort",                     23.7188, 90.3880, NORTH),
    ("ISB", "Islambagh",                        23.7135, 90.3875, NORTH),
    ("CKB", "Chawkbazar",                       23.7175, 90.3955, NORTH),
    ("BNG", "Bangshal",                         23.7172, 90.4060, NORTH),
    ("NYB", "Nayabazar",                        23.7140, 90.4010, NORTH),
    ("MTF", "Mitford (Babubazar Bridge north)", 23.7105, 90.4025, NORTH),
    ("AHM", "Ahsan Manzil",                     23.7087, 90.4065, NORTH),
    ("SDG", "Sadarghat",                        23.7062, 90.4112, NORTH),
    ("WRI", "Wari",                             23.7185, 90.4195, NORTH),
    ("STP", "Sutrapur",                         23.7112, 90.4180, NORTH),
    ("JTB", "Jatrabari",                        23.7100, 90.4340, NORTH),
    ("PTG", "Postogola (bridge north)",         23.6918, 90.4324, NORTH),
    ("KMP", "Kamalapur Railway Station",        23.7330, 90.4260, NORTH),
    ("MNK", "Maniknagar",                       23.7260, 90.4310, NORTH),
    ("RMN", "Ramna Park",                       23.7390, 90.4040, NORTH),
    ("DLK", "Dholaikhal",                       23.7130, 90.4150, NORTH),
    ("GDR", "Gendaria",                         23.7060, 90.4225, NORTH),
    ("SYD", "Sayedabad Bus Terminal",           23.7128, 90.4250, NORTH),
    ("SCL", "Science Lab",                      23.7390, 90.3860, NORTH),
    ("MGD", "Mugda",                            23.7285, 90.4370, NORTH),
    ("STD", "Bangabandhu Stadium",              23.7292, 90.4148, NORTH),
    ("TKT", "Tikatuli",                         23.7230, 90.4225, NORTH),
    ("SHP", "Shyampur",                         23.7075, 90.4420, NORTH),
    ("HZB", "Hazaribagh",                       23.7270, 90.3750, NORTH),
    ("JGT", "Jigatola",                         23.7330, 90.3750, NORTH),

    ("BBS", "Kadamtali (Babubazar Bridge south)", 23.7042, 90.3998, SOUTH),
    ("KMR", "Kamrangirchar",                    23.7040, 90.3830, SOUTH),
    ("MBG", "Mirerbag",                         23.6870, 90.3965, SOUTH),
    ("KLT", "Kalatia",                          23.6800, 90.4010, SOUTH),
    ("SBD", "Subhadya",                         23.6960, 90.3880, SOUTH),
    ("KND", "Konda",                            23.6850, 90.3850, SOUTH),
    ("HZP", "Hazratpur",                        23.6790, 90.3890, SOUTH),
    ("CNK", "Chunkutia",                        23.6890, 90.4160, SOUTH),
    ("JNJ", "Jinjira",                          23.7002, 90.3945, SOUTH),
    ("ATB", "Atibazar",                         23.7000, 90.3800, SOUTH),
    ("AGN", "Aganagar",                         23.7022, 90.4085, SOUTH),
    ("KLD", "Kalindi",                          23.6955, 90.4050, SOUTH),
    ("KRG", "Keraniganj Upazila",               23.6915, 90.3955, SOUTH),
    ("HSN", "Hasnabad",                         23.6865, 90.4105, SOUTH),
    ("PSS", "Postogola Bridge south",           23.6839, 90.4235, SOUTH),
]

# u, v, status   (length is estimated automatically)
ROADS = [
    ("SHB", "TSC", OPEN), ("SHB", "PRS", OPEN), ("TSC", "NLK", OPEN),
    ("TSC", "CZH", OPEN), ("NLK", "AZM", OPEN), ("AZM", "PLS", OPEN),
    ("AZM", "LLB", OPEN), ("PLS", "BKB", OPEN), ("PLS", "DMC", OPEN),
    ("BKB", "DMC", OPEN), ("BKB", "LLB", OPEN), ("BKB", "CKB", OPEN),
    ("DMC", "CZH", OPEN), ("CZH", "PRS", OPEN), ("PRS", "PLT", OPEN),
    ("PRS", "GLS", OPEN), ("PLT", "MTJ", OPEN), ("PLT", "GLS", OPEN),
    ("GLS", "MTJ", OPEN), ("GLS", "FSH", OPEN), ("GLS", "WRI", OPEN),
    ("MTJ", "WRI", OPEN), ("FSH", "BNG", OPEN), ("FSH", "CKB", OPEN),
    ("LLB", "ISB", OPEN), ("LLB", "CKB", BLOCKED),
    ("ISB", "NYB", FLOODED), ("CKB", "NYB", OPEN), ("CKB", "BNG", OPEN),
    ("NYB", "BNG", OPEN), ("NYB", "MTF", OPEN), ("MTF", "AHM", OPEN),
    ("BNG", "AHM", OPEN), ("AHM", "SDG", FLOODED), ("WRI", "STP", FLOODED),
    ("STP", "SDG", OPEN), ("STP", "BNG", OPEN), ("WRI", "JTB", OPEN),
    ("STP", "PTG", OPEN), ("JTB", "PTG", OPEN),
    # bridges over the Buriganga
    ("MTF", "BBS", OPEN), ("PTG", "PSS", OPEN),
    # Keraniganj
    ("BBS", "JNJ", OPEN), ("BBS", "AGN", OPEN), ("JNJ", "ATB", OPEN),
    ("JNJ", "KRG", OPEN), ("AGN", "KLD", FLOODED), ("KLD", "KRG", OPEN),
    ("KLD", "HSN", OPEN), ("KRG", "HSN", OPEN), ("HSN", "PSS", OPEN),
    ("AGN", "PSS", OPEN),
    # added: north bank
    ("MTJ", "KMP", OPEN), ("KMP", "MNK", OPEN), ("WRI", "MNK", OPEN),
    ("MNK", "SYD", OPEN), ("SYD", "JTB", OPEN), ("SYD", "GDR", OPEN),
    ("GDR", "STP", OPEN), ("GDR", "SDG", OPEN), ("DLK", "STP", OPEN),
    ("DLK", "GLS", OPEN), ("DLK", "BNG", FLOODED), ("SHB", "RMN", OPEN),
    ("RMN", "PRS", OPEN), ("RMN", "PLT", OPEN), ("NLK", "SCL", OPEN),
    ("SCL", "SHB", OPEN),
    # added: south bank
    ("ATB", "KMR", OPEN), ("KMR", "JNJ", OPEN), ("KRG", "MBG", OPEN),
    ("MBG", "KLT", OPEN), ("KLT", "HSN", OPEN),
    # added: more north bank
    ("JTB", "SHP", OPEN), ("MNK", "MGD", OPEN), ("MGD", "JTB", OPEN),
    ("STD", "GLS", OPEN), ("STD", "PLT", OPEN), ("STD", "MTJ", OPEN),
    ("STD", "FSH", OPEN), ("TKT", "WRI", OPEN), ("TKT", "MTJ", OPEN),
    ("TKT", "MNK", OPEN), ("TKT", "STD", OPEN), ("HZB", "AZM", OPEN),
    ("HZB", "JGT", OPEN), ("JGT", "NLK", FLOODED), ("HZB", "LLB", OPEN),
    ("SYD", "DLK", OPEN),
    # added: more south bank
    ("SBD", "JNJ", OPEN), ("SBD", "KRG", OPEN), ("SBD", "ATB", OPEN),
    ("SBD", "KND", OPEN), ("KND", "MBG", OPEN), ("KND", "HZP", OPEN),
    ("HZP", "KLT", FLOODED), ("HZP", "MBG", OPEN), ("CNK", "HSN", OPEN),
    ("CNK", "PSS", OPEN), ("CNK", "KLD", OPEN),
]

Position = str   # a node id


@dataclass
class Victim:
    id: str
    pos: Position
    urgency: str        # "high" | "medium" | "low"
    requirement: str    # "ambulance" | "medical_team"


@dataclass
class Resource:
    id: str
    type: str                 # "ambulance" | "medical_team"
    pos: Position
    zone: Tuple[str, ...]     # areas this unit may be dispatched within
    backup: bool = False      # backup units cover every area


@dataclass
class Scenario:
    grid: RoadNetwork          # kept as "grid" so every module keeps the same API
    vehicle_pos: Position
    hospital_pos: Position
    victims: List[Victim]
    resources: List[Resource]


def build_road_network() -> RoadNetwork:
    net = RoadNetwork()
    for node_id, name, lat, lon, area in NODES:
        net.add_node(node_id, name, lat, lon, area)
    for u, v, status in ROADS:
        net.add_road(u, v, status=status, shape=tuple(ROAD_SHAPES.get((u, v), ())))
    return net


def build_default_scenario() -> Scenario:
    net = build_road_network()

    victims = [
        Victim(id="V1", pos="LLB", urgency="high", requirement="ambulance"),
        Victim(id="V2", pos="SDG", urgency="medium", requirement="ambulance"),
        Victim(id="V3", pos="JNJ", urgency="high", requirement="ambulance"),
        Victim(id="V4", pos="WRI", urgency="medium", requirement="medical_team"),
        Victim(id="V5", pos="HSN", urgency="high", requirement="medical_team"),
    ]

    BOTH = (NORTH, SOUTH)
    resources = [
        Resource(id="A1", type="ambulance", pos="SHB", zone=(NORTH,)),
        Resource(id="A2", type="ambulance", pos="KRG", zone=(SOUTH,)),
        Resource(id="A3", type="ambulance", pos="PLT", zone=BOTH, backup=True),
        Resource(id="M1", type="medical_team", pos="MTJ", zone=(NORTH,)),
        Resource(id="M2", type="medical_team", pos="ATB", zone=(SOUTH,)),
        Resource(id="M3", type="medical_team", pos="BKB", zone=BOTH, backup=True),
    ]

    return Scenario(
        grid=net,
        vehicle_pos="FSH",
        hospital_pos="DMC",
        victims=victims,
        resources=resources,
    )
