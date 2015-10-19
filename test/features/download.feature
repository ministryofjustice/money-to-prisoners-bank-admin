Feature: Signing in
  As a signed-in user
  I want to be able to access the downloads page
  So that I download the files

  Scenario: Go to the download page
    Given I am signed in
    Then I should see "Download files"
    And I should see "ADI Journal - refunds"

  Scenario:
    Given I am signed in
    Then I should see a "Download file" link to "/adi/payment/download"
    And I should see a "Download file" link to "/adi/refund/download"
