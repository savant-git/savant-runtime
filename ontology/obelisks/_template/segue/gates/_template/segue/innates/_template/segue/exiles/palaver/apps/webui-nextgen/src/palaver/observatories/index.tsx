import ChatObservatory
  from "./ChatObservatory"

import GuideObservatory
  from "./GuideObservatory"

import TerminalObservatory
  from "./TerminalObservatory"

import Contextarium
  from "../modules/Contextarium"

import SourceStudio
  from "../modules/SourceStudio"

import WorkModule
  from "../modules/WorkModule"

import SystemModule
  from "../modules/SystemModule"

import KindredModule
  from "../modules/kindred-module"

import SearchModule
  from "../modules/search-module"


export function ObservatoryRouter(
  active: string
) {
  switch (active) {
    case "chat":
      return (
        <ChatObservatory />
      )

    case "terminal":
      return (
        <TerminalObservatory />
      )

    case "memory":
      return (
        <Contextarium />
      )

    case "source":
      return (
        <SourceStudio />
      )

    case "kindred":
      return (
        <KindredModule />
      )

    case "search":
      return (
        <SearchModule />
      )

    case "work":
      return (
        <WorkModule />
      )

    case "system":
      return (
        <SystemModule />
      )

    case "guide":
      return (
        <GuideObservatory />
      )

    default:
      return (
        <ChatObservatory />
      )
  }
}
