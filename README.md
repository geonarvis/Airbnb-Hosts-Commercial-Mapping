# airbnb-hosts-visualization

https://www.geonarvis.com/airbnb-hosts-visualization/

The data source of this project is [Inside Airbnb](https://insideairbnb.com/). The basemap comes from a custom Mapbox Studio project, including:

Increased the grayscale of logos, names, and land features

Increased the density of POIs of interest to tourists, such as attractions, landmarks, and transportation stations

You can preview this style through this link Mapbox Studio. In the scatter plot, the size of the scatter points represents the high or low housing prices. At the bottom of the sidebar, you can find a slider to adjust the scatter point style. Here are the steps to use this map:

Interactive Steps of the Project
Step 1: Select a City
Wait for the loading to complete.

Step 2: Select the Current View Mode
There are two modes: Scatter Plot and Heat Map

Step 3: Check the Type of Host You Want to See
The listings held by different types of hosts will change according to the currently selected time:
- Highly Commercial: The top 10% of hosts in the current city.
- Commercial: The top 10% to 25% of hosts in the current city.
- Semi-Commercial: The remaining hosts outside the other four types of landlords)
- Dual Host: Hosts who hold two houses.
- Single Host: Hosts with one property.

Step 4: Drag the Time Bar
Observe the changes in data and the map over time.
Annual Statistics

At the bottom of the interface, there are two types of annual statistics on properties of different types of hosts in the city:

Percentage: The proportion of properties held by each type of host.
Absolute Number: The total count of properties for each type of host.
Notes on Geographic Coordinates
The coordinates of the listing are fuzzy. Airbnb uses a circle with a radius of 150m as a fuzzy buffer to obscure exact locations.
