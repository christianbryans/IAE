AIRPORTS = [
    {"code": "CGK", "name": "Soekarno-Hatta International Airport", "city": "Jakarta", "province": "Banten"},
    {"code": "DPS", "name": "Ngurah Rai International Airport", "city": "Denpasar", "province": "Bali"},
    {"code": "SUB", "name": "Juanda International Airport", "city": "Surabaya", "province": "East Java"},
    {"code": "MES", "name": "Kualanamu International Airport", "city": "Medan", "province": "North Sumatra"},
    {"code": "UPG", "name": "Sultan Hasanuddin International Airport", "city": "Makassar", "province": "South Sulawesi"},
    {"code": "LOP", "name": "Lombok International Airport", "city": "Lombok", "province": "West Nusa Tenggara"},
    {"code": "KNO", "name": "Kualanamu International Airport", "city": "Medan", "province": "North Sumatra"},
    {"code": "PNK", "name": "Supadio International Airport", "city": "Pontianak", "province": "West Kalimantan"},
    {"code": "BTG", "name": "Batu Licin Airport", "city": "Batu Licin", "province": "South Kalimantan"},
    {"code": "BDO", "name": "Husein Sastranegara International Airport", "city": "Bandung", "province": "West Java"},
    {"code": "MLG", "name": "Abdul Rachman Saleh Airport", "city": "Malang", "province": "East Java"},
    {"code": "SRG", "name": "Achmad Yani International Airport", "city": "Semarang", "province": "Central Java"},
    {"code": "JOG", "name": "Adisutjipto International Airport", "city": "Yogyakarta", "province": "Yogyakarta"},
    {"code": "PDG", "name": "Minangkabau International Airport", "city": "Padang", "province": "West Sumatra"},
    {"code": "PLM", "name": "Sultan Mahmud Badaruddin II International Airport", "city": "Palembang", "province": "South Sumatra"},
    {"code": "BTH", "name": "Hang Nadim International Airport", "city": "Batam", "province": "Riau Islands"},
    {"code": "PKU", "name": "Sultan Syarif Kasim II International Airport", "city": "Pekanbaru", "province": "Riau"},
    {"code": "BPN", "name": "Sultan Aji Muhammad Sulaiman Airport", "city": "Balikpapan", "province": "East Kalimantan"},
    {"code": "TRK", "name": "Juwata International Airport", "city": "Tarakan", "province": "North Kalimantan"},
    {"code": "AMQ", "name": "Pattimura International Airport", "city": "Ambon", "province": "Maluku"},
    {"code": "BIK", "name": "Frans Kaisiepo International Airport", "city": "Biak", "province": "Papua"},
    {"code": "DJJ", "name": "Sentani International Airport", "city": "Jayapura", "province": "Papua"},
    {"code": "TTE", "name": "Sultan Babullah Airport", "city": "Ternate", "province": "North Maluku"},
    {"code": "SOQ", "name": "Domine Eduard Osok Airport", "city": "Sorong", "province": "West Papua"},
    {"code": "MDC", "name": "Sam Ratulangi International Airport", "city": "Manado", "province": "North Sulawesi"}
]

def get_airport_suggestions(query):
    """Get airport suggestions based on user input."""
    query = query.lower()
    suggestions = []
    
    for airport in AIRPORTS:
        if (query in airport["code"].lower() or 
            query in airport["name"].lower() or 
            query in airport["city"].lower()):
            suggestions.append({
                "code": airport["code"],
                "name": f"{airport['name']} ({airport['code']})",
                "city": f"{airport['city']}, {airport['province']}"
            })
    
    return suggestions[:5]  # Return top 5 suggestions 