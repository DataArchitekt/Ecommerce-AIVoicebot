from backend.demo.data.seed_products import seed_products
from backend.demo.data.seed_orders import seed_orders
from backend.demo.data.seed_sessions import seed_sessions
from backend.demo.data.seed_faqs import seed_faqs
from backend.demo.data.seed_policies import seed_policies

def seed_all():
    seed_products()
    seed_faqs()
    seed_policies()
    seed_orders()
    seed_sessions()

if __name__ == "__main__":
    seed_all()
