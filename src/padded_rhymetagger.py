from rhymetagger import RhymeTagger


class PaddedRhymeTagger(RhymeTagger):
    def _split_ipa_components(self, ipa):
        components, reduplicant_length = super()._split_ipa_components(ipa)
        target_length = self.syll_max * 2
        if len(components) < target_length:
            components = components + [""] * (target_length - len(components))
        return components, reduplicant_length
