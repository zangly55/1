"""Include the canonical config directory in both source and wheel distributions."""
from pathlib import Path
import shutil
from setuptools import setup
from setuptools.command.build_py import build_py


class BuildWithConfig(build_py):
    def run(self):
        super().run()
        source = Path(__file__).parent / "config"
        destination = Path(self.build_lib) / "cvalarm" / "resources" / "config"
        for item in source.rglob("*.json"):
            target = destination / item.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item, target)


setup(cmdclass={"build_py": BuildWithConfig})
