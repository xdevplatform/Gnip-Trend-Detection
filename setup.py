from setuptools import setup,find_packages

setup(name='gnip_trend_detection' 
        ,version='0.1'
        ,description='Trend/spike detection on time series from Twitter'
        ,url='https://github.com/jeffakolb/Gnip-Trend-Detection'
        ,author='Jeff Kolb'
        ,email='jeffakolb@gmail.com'
        ,license='MIT'
        ,packages=find_packages()
        ,install_requires=['scipy','sklearn','matplotlib'] 
        ,scripts=['analyze.py','rebin.py','plot.py','analyze_all_rules.py']  
        )
