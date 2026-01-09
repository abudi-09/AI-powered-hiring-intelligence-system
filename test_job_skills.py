"""
Smoke test for Job-Skill mapping functionality
Tests Step 7 requirements
"""
import asyncio
import sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.skill import Skill
from app.models.job import Job
from app.models.job_skill import JobSkill
from app.core.security import get_password_hash


async def main():
    print("=" * 60)
    print("Step 7 Smoke Test: Job-Skill Mapping")
    print("=" * 60)
    
    # Get a database session
    async for db in get_db():
        try:
            # 1. Check admin user exists
            print("\n[1/7] Checking admin user...")
            result = await db.execute(select(User).where(User.email == "admin@example.com"))
            admin = result.scalar_one_or_none()
            if not admin:
                print("✗ Admin user not found, creating...")
                admin = User(
                    email="admin@example.com",
                    hashed_password=get_password_hash("admin123"),
                    full_name="Admin User",
                    role=UserRole.Admin,
                    is_active=True
                )
                db.add(admin)
                await db.commit()
                await db.refresh(admin)
            print(f"✓ Admin user found: {admin.email} (role: {admin.role})")
            
            # 2. Create test skills
            print("\n[2/7] Creating test skills...")
            skills_data = [
                ("Python", "Programming Language"),
                ("React", "Frontend Framework"),
                ("SQL", "Database"),
            ]
            skills = []
            for name, category in skills_data:
                result = await db.execute(select(Skill).where(Skill.name == name))
                skill = result.scalar_one_or_none()
                if not skill:
                    skill = Skill(name=name, category=category)
                    db.add(skill)
                skills.append(skill)
            
            await db.commit()
            for skill in skills:
                await db.refresh(skill)
            print(f"✓ Created/found {len(skills)} skills: {[s.name for s in skills]}")
            
            # 3. Create job with weighted skills
            print("\n[3/7] Creating job with weighted skills...")
            job = Job(
                title="Senior Full Stack Developer",
                description="We need someone with strong backend and frontend skills",
                owner_id=admin.id
            )
            db.add(job)
            await db.flush()
            
            # Attach skills with weights
            job_skills = [
                JobSkill(job_id=job.id, skill_id=skills[0].id, weight=0.9),  # Python 0.9
                JobSkill(job_id=job.id, skill_id=skills[1].id, weight=0.7),  # React 0.7
                JobSkill(job_id=job.id, skill_id=skills[2].id, weight=0.6),  # SQL 0.6
            ]
            for js in job_skills:
                db.add(js)
            
            await db.commit()
            await db.refresh(job)
            print(f"✓ Job created: {job.title} (ID: {job.id})")
            
            # 4. Verify response includes skill_name + weight
            print("\n[4/7] Verifying job-skill associations...")
            result = await db.execute(
                select(JobSkill.skill_id, Skill.name, JobSkill.weight)
                .join(Skill, Skill.id == JobSkill.skill_id)
                .where(JobSkill.job_id == job.id)
                .order_by(JobSkill.weight.desc())
            )
            job_skill_rows = result.all()
            
            if len(job_skill_rows) != 3:
                print(f"✗ Expected 3 skills, found {len(job_skill_rows)}")
                return False
            
            print("✓ Job skills retrieved:")
            for skill_id, skill_name, weight in job_skill_rows:
                print(f"  - {skill_name}: {weight}")
            
            # 5. Update job to replace skills (keep only Python)
            print("\n[5/7] Updating job to replace skills...")
            # Clear existing skills
            await db.execute(
                JobSkill.__table__.delete().where(JobSkill.job_id == job.id)
            )
            # Add only Python with updated weight
            new_skill = JobSkill(job_id=job.id, skill_id=skills[0].id, weight=1.0)
            db.add(new_skill)
            await db.commit()
            
            # Verify update
            result = await db.execute(
                select(JobSkill.skill_id, Skill.name, JobSkill.weight)
                .join(Skill, Skill.id == JobSkill.skill_id)
                .where(JobSkill.job_id == job.id)
            )
            updated_skills = result.all()
            
            if len(updated_skills) != 1:
                print(f"✗ Expected 1 skill after update, found {len(updated_skills)}")
                return False
            
            print(f"✓ Skills updated successfully: {updated_skills[0][1]} ({updated_skills[0][2]})")
            
            # 6. Test cascade delete (delete job should remove job_skills)
            print("\n[6/7] Testing cascade delete...")
            job_id = job.id
            await db.delete(job)
            await db.commit()
            
            # Check if job_skills were deleted
            result = await db.execute(
                select(JobSkill).where(JobSkill.job_id == job_id)
            )
            remaining = result.scalars().all()
            
            if remaining:
                print(f"✗ Found {len(remaining)} orphan job_skills after job deletion")
                return False
            
            print("✓ Cascade delete working: no orphan job_skills")
            
            # 7. Test composite primary key constraint
            print("\n[7/7] Testing composite PK constraint...")
            # Create new job
            job2 = Job(
                title="Backend Developer",
                description="Python specialist",
                owner_id=admin.id
            )
            db.add(job2)
            await db.flush()
            
            # Add Python skill
            js1 = JobSkill(job_id=job2.id, skill_id=skills[0].id, weight=0.8)
            db.add(js1)
            await db.commit()
            
            # Try to add same skill again (should fail)
            try:
                js2 = JobSkill(job_id=job2.id, skill_id=skills[0].id, weight=0.9)
                db.add(js2)
                await db.commit()
                print("✗ Duplicate job-skill pair was allowed (composite PK failed)")
                await db.rollback()
                return False
            except Exception as e:
                await db.rollback()
                print(f"✓ Composite PK working: duplicate rejected ({type(e).__name__})")
            
            # Cleanup
            await db.delete(job2)
            await db.commit()
            
            print("\n" + "=" * 60)
            print("✓ ALL TESTS PASSED")
            print("=" * 60)
            return True
            
        except Exception as e:
            print(f"\n✗ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
