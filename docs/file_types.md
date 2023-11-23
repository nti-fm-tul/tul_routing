
# Supported file types
The supported formats include '.gpx,' '.kml,' '.tcx,' '.geojson,' '.csv,' and '.json.' 

## KLM

KLM example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
    <Placemark>
      <name>Trasa z místa praha do místa Mnichovo Hradiště</name>
      <styleUrl>#line-1267FF-5000-nodesc</styleUrl>
      <LineString>
        <tessellate>1</tessellate>
        <coordinates>
          14.43775,50.07553,0
          14.43774,50.07561,0
          <!--další souřadnice byly vynechány pro přehlednost-->
          14.97197,50.52687,0
        </coordinates>
    </LineString>
  </Placemark>
</kml>
```

## GPX

GPX example exported from [mapy.cz](http://mapy.cz)

```xml
<?xml version="1.0" encoding="utf-8"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" version="1.1" creator="https://mapy.cz/">
	<trk>
		<name>Route from 50.780596N, 15.055135E to Generála Svobody</name>
		<trkseg>
			<trkpt lat="50.780396" lon="15.055316">
				<ele>374.000000</ele>
			</trkpt>
            <trkpt lat="50.780442" lon="15.055450">
				<ele>375.000000</ele>
			</trkpt>
            <!-- další souřadnice byly vynechány pro přehlednost -->
            <trkpt lat="50.779630" lon="15.054201">
				<ele>362.000000</ele>
			</trkpt>
        </trkseg>
    </trk>
</gpx>
```


## TCX

TCX example

```xml
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<TrainingCenterDatabase ...>
  <Activities>
    <Activity Sport="Biking">
      <Id>2010-06-26T10:06:11Z</Id>
      <Lap StartTime="2010-06-26T10:06:11Z">
        <TotalTimeSeconds>906.1800000</TotalTimeSeconds>
        <!-- další statistiky byly vynechány pro přehlednost -->
        <Track>
          <Trackpoint>
            <Time>2010-06-26T10:06:11Z</Time>
            <Position>
              <LatitudeDegrees>40.7780135</LatitudeDegrees>
              <LongitudeDegrees>-73.9665795</LongitudeDegrees>
            </Position>
            <AltitudeMeters>36.1867676</AltitudeMeters>
            <!-- další informace byly vynechány pro přehlednost -->
          </Trackpoint>
        </Track>
      </Lap>
    </Activity>
  </Activities>
</TrainingCenterDatabase>
```

## GeoJSON

GeoJSON example

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "name": "Route from 50.780596N, 15.055135E to Generála Svobody",
        "styleUrl": "#line-1267FF-5000-nodesc"
      },
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [
            15.055316,
            50.780396
          ],
          [
            15.05545,
            50.780442
          ],
          /* další souřadnice byly vynechány pro přehlednost */
          [
            15.054201,
            50.77963
          ]
        ]
      }
    }
  ]
}
```

## CSV

CSV example

```csv
index,timestamp,latitude,longitude
0,1610531240,50.780396,15.055316
1,1610531277,50.780442,15.05545
# další souřadnice byly vynechány pro přehlednost
2,1610531541,50.77963,15.054201
```

## Entry JSON

Entry JSON example. This format was specific for the original project purposes. 

```json
{
    "Id": "x5sn54qwds4",
    "Name": "EUT TestRoute",
    "Timestamp": "2023-07-04T04:54:10Z",
    "Segments": [{
            "Id": "x5sn54qwds4-1",
            "Points": [{
                    "Time": 0,
                    "Latitude": 50.41885,
                    "Longitude": 14.9099833333333,
                    "Speed": null,

                },
                // další souřadnice byly vynechány pro přehlednost
                {
                    "Time": 0,
                    "Latitude": 50.41885,
                    "Longitude": 14.9099,
                    "Speed": null,
                }
            ]
    }]
}
```
