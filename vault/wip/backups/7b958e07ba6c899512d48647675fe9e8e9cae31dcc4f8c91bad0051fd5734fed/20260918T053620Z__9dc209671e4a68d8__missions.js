export const missions = [
  {
    id: "artemis-i",
    numeral: "I",
    year: "2022",
    status: "COMPLETE",
    title: "The architecture leaves Earth",
    shortTitle: "Integrated Flight Test",
    destination: "Moon",
    crew: "Uncrewed",
    distance: "1.4 million mi",
    duration: "25 d 10 h 53 m",
    description:
      "Artemis I demonstrated the integrated Space Launch System and Orion spacecraft during an uncrewed journey beyond the Moon and back to Earth.",
    phases: [
      "Launch",
      "Earth departure",
      "Lunar flyby",
      "Distant retrograde orbit",
      "Return",
      "Reentry",
      "Splashdown"
    ]
  },

  {
    id: "artemis-ii",
    numeral: "II",
    year: "2026",
    status: "COMPLETE",
    title: "Humans return to lunar space",
    shortTitle: "Crewed Lunar Flight",
    destination: "Lunar vicinity",
    crew: "4",
    distance: "Lunar trajectory",
    duration: "Approx. 10 days",
    description:
      "Artemis II advances the program into crewed flight, validating Orion and its supporting systems with astronauts aboard.",
    phases: [
      "Launch",
      "Earth orbit",
      "Systems demonstration",
      "Trans-lunar trajectory",
      "Lunar vicinity",
      "Return",
      "Splashdown"
    ]
  },

  {
    id: "artemis-iii",
    numeral: "III",
    year: "2027",
    status: "PLANNED",
    title: "Integrated systems demonstration",
    shortTitle: "Crewed Demonstration",
    destination: "Low Earth orbit",
    crew: "Crewed",
    distance: "Low Earth orbit",
    duration: "Mission dependent",
    description:
      "Artemis III advances integrated crewed systems and operations through a demonstration mission designed to mature the architecture for subsequent lunar surface missions.",
    phases: [
      "Launch",
      "Earth orbit",
      "Integrated operations",
      "Systems demonstration",
      "Return",
      "Reentry"
    ]
  },

  {
    id: "artemis-iv",
    numeral: "IV",
    year: "2028",
    status: "PLANNED",
    title: "Return to the lunar surface",
    shortTitle: "Lunar Surface Mission",
    destination: "Moon",
    crew: "Crewed",
    distance: "Lunar surface",
    duration: "Mission dependent",
    description:
      "Artemis IV is part of the evolving campaign toward sustained crewed lunar exploration and expanded infrastructure around and on the Moon.",
    phases: [
      "Launch",
      "Trans-lunar injection",
      "Lunar arrival",
      "Lunar operations",
      "Surface operations",
      "Ascent",
      "Return"
    ]
  },

  {
    id: "artemis-v",
    numeral: "V",
    year: "2028+",
    status: "PLANNED",
    title: "Build the lunar frontier",
    shortTitle: "Sustained Exploration",
    destination: "Moon",
    crew: "Crewed",
    distance: "Lunar architecture",
    duration: "Mission dependent",
    description:
      "Later Artemis missions expand the infrastructure, mobility, science capability and operational experience needed for a sustained human presence at the Moon.",
    phases: [
      "Launch",
      "Lunar transit",
      "Gateway operations",
      "Surface deployment",
      "Science",
      "Mobility",
      "Return"
    ]
  }
];

export const systems = [
  {
    id: "sls",
    index: "01",
    name: "Space Launch System",
    shortName: "SLS",
    type: "Heavy-lift launch vehicle",
    description:
      "The launch system that sends Orion, astronauts and mission hardware away from Earth."
  },

  {
    id: "orion",
    index: "02",
    name: "Orion",
    shortName: "ORION",
    type: "Crew spacecraft",
    description:
      "The spacecraft designed to transport astronauts through deep space and return its crew safely to Earth."
  },

  {
    id: "egs",
    index: "03",
    name: "Exploration Ground Systems",
    shortName: "EGS",
    type: "Launch infrastructure",
    description:
      "The ground architecture responsible for processing, integration, launch and recovery support."
  },

  {
    id: "gateway",
    index: "04",
    name: "Gateway",
    shortName: "GATEWAY",
    type: "Lunar orbital infrastructure",
    description:
      "A lunar-orbiting platform intended to support science, exploration and increasingly complex missions."
  },

  {
    id: "hls",
    index: "05",
    name: "Human Landing System",
    shortName: "HLS",
    type: "Lunar transportation",
    description:
      "Human landing systems provide transportation between lunar orbit and the surface for Artemis landing missions."
  },

  {
    id: "surface",
    index: "06",
    name: "Surface Systems",
    shortName: "SURFACE",
    type: "Exploration infrastructure",
    description:
      "Spacesuits, mobility, power, science equipment and surface infrastructure extend the reach and duration of lunar crews."
  }
];
