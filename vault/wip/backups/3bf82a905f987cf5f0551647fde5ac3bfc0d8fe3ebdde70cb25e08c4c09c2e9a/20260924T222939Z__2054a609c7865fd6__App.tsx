import Palaver from "./palaver/Palaver"
import PalaverBoundary from "./palaver/PalaverBoundary"
import PalaverKeyboardHelp from "./palaver/PalaverKeyboardHelp"
import PalaverPatchReview from "./palaver/PalaverPatchReview"

export default function App() {
  return (
    <PalaverBoundary>
      <Palaver />
      <PalaverKeyboardHelp />
      <PalaverPatchReview />
    </PalaverBoundary>
  )
}
