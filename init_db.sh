#!/bin/bash

# Create data directory if it doesn't exist
mkdir -p data

# Initialize database
python database.py

# Insert default airlines
sqlite3 data/database.db <<EOF
INSERT INTO airlines (name, code, logo_url, base_price) VALUES
('Garuda Indonesia', 'GA', 'https://logos-world.net/wp-content/uploads/2023/01/Garuda-Indonesia-Logo.png', 1500000),
('Lion Air', 'JT', 'https://download.logo.wine/logo/Lion_Air/Lion_Air-Logo.wine.png', 1000000),
('AirAsia', 'QZ', 'https://1000logos.net/wp-content/uploads/2020/04/AirAsia-Logo-2009.jpg', 800000),
('Citilink', 'QG', 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/2012_Citilink_Logo.svg/1200px-2012_Citilink_Logo.svg.png', 900000),
('Batik Air', 'ID', 'https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjdybdonaiWYpknLpLbdDZI_Qls90OIZkaKPyrmwnCB4A-C6Cxeyy1j-HrSiwKJAfMuI28rrNPz-jN_8LESqtvV6sPW4ZJ2h5Leou7yGWZBsfPFLTbfwYWrWlOG6iItpZM2ikhnggO1b6E/s2048/Logo+Batik+Air+%2528Cover%2529.png', 1200000);
EOF

# Start Flask
flask run --host=0.0.0.0 