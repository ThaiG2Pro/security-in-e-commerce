# init_products.py
# Script to force-insert initial products into the database
from models import populate_sample_data

if __name__ == '__main__':
    populate_sample_data()
    print('Initial products inserted (if not already present).')
