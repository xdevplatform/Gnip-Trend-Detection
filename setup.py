from setuptools import setup,find_packages

setup(name='gnip_trend_detection' 
        ,version='0.3'
        ,description='Trend/spike detection on time series from Twitter'
        ,url='https://github.com/jeffakolb/Gnip-Trend-Detection'
        ,author='Jeff Kolb'
        ,author_email='jeffakolb@gmail.com'
        ,license='MIT'
        ,packages=find_packages()
        ,install_requires=['scipy','sklearn','datetime_truncate'] 
        ,extras_require={'plotting':['matplotlib']}
        ,scripts=['trend_analyze.py',
            'trend_rebin.py',
            'trend_plot.py',
            'trend_analyze_many.py',
            'time_series_correlations.py',
            'trend_detector.py',
            ]  
        )
