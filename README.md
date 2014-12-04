Puller
===
Worker for pulling data from remote HM sensors.

Setup for Linux
---
### Dependencies Setup
In the root of Pull, execute `pip install -r requirements.txt`.

### Database Setup
1. Edit `alembic.ini`. Replace the default `sqlalchemy.url` with yours.
2. (optional) Edit `migrations/env.py`. Find `target_metadata = Base.metadata` and 
	replace with your metadata.
3. `cd` to the root of Puller. Then type command `alembic revision --auto-generate -m 'your comment'`.
4. Execute `alembic upgrade head`

Note: You need to execute **Step 3** and **Step 4** every time you change the models. 
