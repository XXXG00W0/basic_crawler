from setuptools import setup, find_packages

VERSION = '0.0.1' 
DESCRIPTION = 'A general wraparound module based on Selenium'
LONG_DESCRIPTION = 'A general wraparound module based on Selenium'

# 配置
setup(
       # 名称必须匹配文件名 'verysimplemodule'
        name="basic_crawler", 
        version=VERSION,
        author="Ziyi Liang",
        author_email="<hower36@163.com>",
        description=DESCRIPTION,
        long_description=LONG_DESCRIPTION,
        packages=find_packages(),
        install_requires=['selenium >= 4.9.1', 'pyperclip >= 1.8.2', 'PyAutoGUI >= 0.9.53'], # add any additional packages that 
        # 需要和你的包一起安装，例如：'caer'
        
        keywords=['python', 'first package'],
        classifiers= [
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Education",
            "Programming Language :: Python :: 2",
            "Programming Language :: Python :: 3",
            "Operating System :: MacOS :: MacOS X",
            "Operating System :: Microsoft :: Windows",
        ]
)