# run_apply.py
import sys, json, asyncio
from apply_runner import apply_to_job

def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

async def main():
    if len(sys.argv) < 7:
        print("Usage: python run_apply.py <job_url> <applicant.json> <base_resume.json> <company> <role> <jd.txt>")
        sys.exit(1)

    job_url = sys.argv[1]
    applicant = read_json(sys.argv[2])
    base_resume = read_json(sys.argv[3])
    company = sys.argv[4]
    role = sys.argv[5]
    job_desc = read_text(sys.argv[6])

    result = await apply_to_job(
        job_url=job_url,
        applicant=applicant,
        base_resume=base_resume,
        job_meta={"company": company, "role": role, "job_desc": job_desc}
    )
    print(result)

if __name__ == "__main__":
    asyncio.run(main())