/*
 * This file is part of Invenio.
 * Copyright (C) 2017-2020 CERN.
 *
 * Invenio is free software; you can redistribute it and/or modify it
 * under the terms of the MIT License; see LICENSE file for more details.
 */
import React, { useState } from "react";
import ReactDOM from "react-dom";
import { Formik, Form } from "formik";
import * as Yup from "yup";
import axios from "axios";
import _ from "lodash";
import { TextInput, SelectInput, RichInput } from "./forms";

const COMMUNITY_TYPES = [
  { id: "organization", display: "Institution/Organization" },
  { id: "event", display: "Event" },
  { id: "topic", display: "Topic" },
  { id: "project", display: "Project" }
];

const VISIBILITY_TYPES = [
  { id: "public", display: "Public" },
  { id: "private", display: "Private" },
  { id: "hidden", display: "Hidden" }
];

const CommunityCreateForm = () => {
  const [globalError, setGlobalError] = useState(null);
  return (
    <div className="container">
      <h1>Create a community</h1>
      <Formik
        initialValues={{
          id: "",
          description: "",
          title: "",
          // curation_policy: "",
          // page: "",
          type: "event",
          website: "",
          visibility: "public"
          // funding: "",
          // domain: ""
        }}
        validationSchema={Yup.object({
          id: Yup.string()
            .required("Required")
            .max(32, "Must be 32 characters or less"),
          description: Yup.string()
            .required("Required")
            .max(250, "Must be 250 characters or less"),
          title: Yup.string()
            .max(120, "Must be 120 characters or less")
            .required("Required"),
          // curation_policy: Yup.string().max(
          //   250,
          //   "Must be 250 characters or less"
          // ),
          // page: Yup.string().max(250, "Must be 250 characters or less"),
          type: Yup.string()
            .required("Required")
            .oneOf(
              COMMUNITY_TYPES.map(c => {
                return c.id;
              })
            ),
          visibility: Yup.string()
            .required("Required")
            .oneOf(
              VISIBILITY_TYPES.map(c => {
                return c.id;
              })
            ),
          website: Yup.string().url("Must be a valid URL")
          // funding: Yup.string().max(250, "Must be 250 characters or less"),
          // domain: Yup.string().max(250, "Must be 250 characters or less")
        })}
        onSubmit={(values, { setSubmitting, setErrors, setFieldError }) => {
          setSubmitting(true);
          const payload = _.pickBy(values, val => val !== "" && !_.isNil(val));
          axios
            .post("/api/communities/", payload)
            .then(response => {
              console.log(response);
              window.location.href = "/communities";
            })
            .catch(error => {
              // TODO: handle nested fields
              if (error.response.data.errors) {
                error.response.data.errors.map(({ field, message }) =>
                  setFieldError(field, message)
                );
              } else if (error.response.data.message) {
                setGlobalError(error.response.data.message);
              }
              console.log(error.response.data);
            })
            .finally(() => setSubmitting(false));
        }}
      >
        {({ isSubmitting, isValid }) => (
          <Form>
            <TextInput label="ID" placeholder="biosyslit" name="id" />
            <TextInput label="Title" placeholder="BLR" name="title" />
            <SelectInput choices={COMMUNITY_TYPES} label="Type" name="type" />
            <RichInput label="Description" name="description" />
            <TextInput
              label="Website"
              placeholder="https://example.org"
              name="website"
            />
            <SelectInput
              choices={VISIBILITY_TYPES}
              label="Visibility"
              name="visibility"
            />
            <button
              disabled={!isValid || isSubmitting}
              className="btn"
              type="submit"
            >
              Submit
            </button>
            {globalError ? (
              <div className="help-block">{globalError}</div>
            ) : null}
          </Form>
        )}
      </Formik>
    </div>
  );
};

ReactDOM.render(<CommunityCreateForm />, document.getElementById("app"));

export default CommunityCreateForm;
