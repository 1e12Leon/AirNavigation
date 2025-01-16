import airsim


class WeatherController:
    def __init__(self):
        self.client = airsim.MultirotorClient()
        self.client.enableApiControl(True)
        self.client.simEnableWeather(True)

        self.__weather_type = 'none'
        self.__weather_val = 0

    def get_weather(self):
        return self.__weather_type, self.__weather_val

    def change_weather(self, weather_type, val):
        self.__weather_type = weather_type
        self.__weather_val = val

        self.client.simSetWeatherParameter(airsim.WeatherParameter.Rain, 0)
        self.client.simSetWeatherParameter(airsim.WeatherParameter.Snow, 0)
        self.client.simSetWeatherParameter(airsim.WeatherParameter.Dust, 0)
        self.client.simSetWeatherParameter(airsim.WeatherParameter.Fog, 0)

        val /= 100

        if weather_type == 'rain':
            self.client.simSetWeatherParameter(airsim.WeatherParameter.Rain, val)
        if weather_type == 'snow':
            self.client.simSetWeatherParameter(airsim.WeatherParameter.Snow, val)
        if weather_type == 'dust':
            self.client.simSetWeatherParameter(airsim.WeatherParameter.Dust, val)
        if weather_type == 'Fog':
            self.client.simSetWeatherParameter(airsim.WeatherParameter.Fog, val)
